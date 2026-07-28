"""WinUSB driver binding via Win32 SetupAPI (Zadig-equivalent, silent).

Binds Windows' inbox ``winusb.sys`` to TRCC's USB bulk/LY LCD devices
without requiring a signed INF.  Uses the same Win32 API approach Zadig
uses on Windows 10/11:

  1. ``SetupDiGetClassDevs`` — open a device info set for all USB devices.
  2. ``SetupDiEnumDeviceInfo`` — walk the set looking for our VID/PID.
  3. ``SetupDiSetDeviceRegistryProperty(SPDRP_SERVICE)`` — set the
     device's driver service to ``winusb`` directly in the registry.
  4. ``SetupDiCallClassInstaller(DIF_PROPERTYCHANGE)`` — restart the
     device so Windows loads ``winusb.sys``.

This bypasses INF signature requirements entirely -- we're not installing
a new driver, just pointing the device at an already-signed Microsoft
driver that's in the driver store.

Requires Administrator (the packaged app has it via ``uac_admin``).
No user interaction needed -- fully silent.
"""
from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)

# Win32 constants
DIGCF_ALLCLASSES = 0x00000040
DIGCF_PRESENT = 0x00000002
DIF_PROPERTYCHANGE = 0x00000012
DICS_ENABLE = 0x00000001
DICS_FLAG_GLOBAL = 0x00000001
SPDRP_HARDWAREID = 0x00000000
SPDRP_SERVICE = 0x00000004

# USB class GUID: {36fc9e60-c465-11cf-8056-444553540000}
_USB_CLASS_GUID_BYTES = (
    0x60, 0x9e, 0xfc, 0x36, 0x65, 0xc4, 0xcf, 0x11,
    0x80, 0x56, 0x44, 0x45, 0x53, 0x54, 0x00, 0x00,
)

# WinUSB service name (matches the inbox winusb.sys service).
_WINUSB_SERVICE = "winusb"

# TRCC devices that need WinUSB binding (USB bulk / LY LCD).
_BIND_DEVICES: list[tuple[int, int]] = [
    (0x0416, 0x5406),  # Elite Vision 360 (BULK_ALI)
    (0x87AD, 0x70DB),  # GrandVision 360 AIO (BULK)
    (0x0416, 0x5408),  # Trofeo Vision 9.16 (LY)
    (0x0416, 0x5409),  # Trofeo Vision 9.16 (LY)
]


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", ctypes.c_byte * 16),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class SP_CLASSINSTALL_HEADER(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InstallFunction", wintypes.DWORD),
    ]


class SP_PROPCHANGE_PARAMS(ctypes.Structure):
    _fields_ = [
        ("ClassInstallHeader", SP_CLASSINSTALL_HEADER),
        ("StateChange", wintypes.DWORD),
        ("Scope", wintypes.DWORD),
        ("HwProfile", wintypes.DWORD),
    ]


_setupapi: ctypes.WinDLL | None = None


def _load_dll() -> bool:
    global _setupapi
    if not sys.platform.startswith("win"):
        return False
    if _setupapi is None:
        try:
            _setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
        except OSError as e:
            log.warning("winusb_bind: setupapi.dll load failed: %s", e)
            return False
    return True


def _get_hardware_id(dev_info, did_data: SP_DEVINFO_DATA) -> str | None:
    assert _setupapi is not None
    buf = ctypes.create_unicode_buffer(512)
    required = wintypes.DWORD(0)
    prop_type = wintypes.DWORD(0)
    ok = _setupapi.SetupDiGetDeviceRegistryPropertyW(
        dev_info, ctypes.byref(did_data), SPDRP_HARDWAREID,
        ctypes.byref(prop_type),
        ctypes.cast(buf, wintypes.LPBYTE), 512 * 2,
        ctypes.byref(required),
    )
    if not ok:
        return None
    return buf.value


def _set_service(dev_info, did_data: SP_DEVINFO_DATA, service: str) -> bool:
    assert _setupapi is not None
    data = (service + "\0").encode("utf-16-le")
    ok = _setupapi.SetupDiSetDeviceRegistryPropertyW(
        dev_info, ctypes.byref(did_data), SPDRP_SERVICE,
        ctypes.cast(ctypes.c_char_p(data), wintypes.LPBYTE), len(data),
    )
    if not ok:
        err = ctypes.get_last_error()
        log.warning("winusb_bind: SetDeviceRegistryProperty(SERVICE) failed (err=%d)", err)
        return False
    return True


def _restart_device(dev_info, did_data: SP_DEVINFO_DATA) -> bool:
    assert _setupapi is not None
    params = SP_PROPCHANGE_PARAMS()
    params.ClassInstallHeader.cbSize = ctypes.sizeof(SP_CLASSINSTALL_HEADER)
    params.ClassInstallHeader.InstallFunction = DIF_PROPERTYCHANGE
    params.StateChange = DICS_ENABLE
    params.Scope = DICS_FLAG_GLOBAL
    params.HwProfile = 0

    ok = _setupapi.SetupDiSetClassInstallParamsW(
        dev_info, ctypes.byref(did_data),
        ctypes.byref(params), ctypes.sizeof(params),
    )
    if not ok:
        err = ctypes.get_last_error()
        log.warning("winusb_bind: SetClassInstallParams failed (err=%d)", err)
        return False

    ok = _setupapi.SetupDiCallClassInstaller(
        DIF_PROPERTYCHANGE, dev_info, ctypes.byref(did_data),
    )
    if not ok:
        err = ctypes.get_last_error()
        log.warning("winusb_bind: CallClassInstaller failed (err=%d)", err)
        return False
    return True


def _find_and_bind(vid: int, pid: int) -> bool:
    assert _setupapi is not None

    # Open a device info set for all present devices.
    class_guid = (ctypes.c_byte * 16)(*_USB_CLASS_GUID_BYTES)
    dev_info = _setupapi.SetupDiGetClassDevsW(
        ctypes.byref(class_guid),
        None, None, DIGCF_PRESENT | DIGCF_ALLCLASSES,
    )
    # INVALID_HANDLE_VALUE check (c_void_p restype returns int or None)
    if not dev_info or dev_info == ctypes.c_void_p(-1).value:
        err = ctypes.get_last_error()
        log.warning("winusb_bind: SetupDiGetClassDevs failed (err=%d)", err)
        return False

    try:
        target_id = f"USB\\VID_{vid:04X}&PID_{pid:04X}".upper()
        index = 0
        did = SP_DEVINFO_DATA()
        did.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
        while True:
            if not _setupapi.SetupDiEnumDeviceInfo(dev_info, index, ctypes.byref(did)):
                # No more devices -- target not found (unplugged).
                return True  # Not a failure
            hw_id = _get_hardware_id(dev_info, did)
            if hw_id and target_id in hw_id.upper():
                log.info("winusb_bind: found %s, binding winusb", hw_id)
                if not _set_service(dev_info, did, _WINUSB_SERVICE):
                    return False
                if not _restart_device(dev_info, did):
                    log.warning("winusb_bind: device restart failed -- may need replug")
                    return False
                log.info("winusb_bind: %s bound to winusb.sys", target_id)
                return True
            index += 1
    finally:
        _setupapi.SetupDiDestroyDeviceInfoList(dev_info)


def bind_winusb_silent(inf_path: Path | None = None) -> bool:
    """Bind winusb.sys to all TRCC bulk/LY devices.

    Uses SetupAPI to directly set the device's driver service to
    ``winusb`` in the registry, then restarts the device.  No INF
    signature required -- we're pointing at an already-signed Microsoft
    driver in the driver store.

    Args:
        inf_path: Unused (kept for API compatibility).  The INF is not
            needed for this binding method.

    Returns True if all bindings succeeded (or devices are unplugged).
    Requires Administrator privileges.
    """
    if not _load_dll():
        return False

    all_ok = True
    for vid, pid in _BIND_DEVICES:
        try:
            if not _find_and_bind(vid, pid):
                all_ok = False
        except Exception as e:
            log.warning("winusb_bind: %04x:%04x failed: %s: %s", vid, pid, type(e).__name__, e)
            all_ok = False

    if all_ok:
        log.info("winusb_bind: all device bindings processed")
    return all_ok

"""Windows WinUSB driver diagnostic + automatic setup.

The Windows analog of the Linux ``_udev.py`` and FreeBSD ``_devd.py``
installers.  Historically Windows couldn't silently install kernel
drivers without a signed driver package, so this module only diagnosed
the state and printed Zadig instructions.  As of 2026-07-16 the app
bundles a WinUSB INF that references Windows' inbox ``winusb.sys`` —
installed silently via ``pnputil /add-driver`` (admin-only, which the
packaged app already has via its UAC manifest).

What's actually needed
----------------------
For pyusb / libusb to talk to a TRCC device on Windows, the device's
USB interface must be bound to ``WinUSB.sys`` (or ``libusbK``,
``libusb-win32``).  Windows' default behaviour for a generic USB
device is to bind it to no driver at all (or the wrong one), so libusb
fails with ``NoBackendError`` until WinUSB is bound.

This wizard:

  1. Tries to enumerate every device in the registry via pyusb.
  2. For each device that is **physically present but invisible to
     pyusb**, attempts silent WinUSB installation via the bundled INF
     + ``pnputil``.
  3. If silent install fails, falls back to printed Zadig instructions
     (https://zadig.akeo.ie/) as a manual fallback.
  4. Returns 0 if every present device is visible, 1 if any still need
     driver work, 2 if pyusb itself isn't usable (libusb-1.0.dll
     missing from PATH — separate fix).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from ...core.registry import ALL_DEVICES, Wire

log = logging.getLogger(__name__)


_ZADIG_URL = "https://zadig.akeo.ie/"

# Devices that need WinUSB (USB bulk / libusb access).
# HID devices use Windows' built-in HID driver; SCSI devices use the
# mass-storage driver — neither needs WinUSB.
_WINUSB_WIRES: frozenset[Wire] = frozenset({Wire.BULK, Wire.BULK_ALI, Wire.LY})


def _bundled_inf_path() -> Path | None:
    """Locate the bundled ``trcc_winusb.inf`` next to the exe or in the
    package's ``assets/drivers/`` folder."""
    candidates: list[Path] = []
    exe_dir = Path(sys.executable).parent
    # PyInstaller onedir layout
    candidates.append(exe_dir / "_internal" / "trcc" / "assets" / "drivers" / "trcc_winusb.inf")
    # Portable folder layout (next to exe)
    candidates.append(exe_dir / "drivers" / "trcc_winusb.inf")
    # Source / dev layout
    here = Path(__file__).resolve().parent
    candidates.append(here.parent.parent.parent / "assets" / "drivers" / "trcc_winusb.inf")
    for p in candidates:
        if p.is_file():
            log.debug("winusb inf: found at %s", p)
            return p
    log.debug("winusb inf: not found in any candidate location")
    return None


def install_winusb_silent() -> bool:
    """Bind Windows' inbox ``winusb.sys`` to TRCC's bulk/LY LCD devices.

    Uses the Win32 SetupAPI directly (``SetupCopyOEMInf`` +
    ``UpdateDriverForPlugAndPlayDevices``) — the same mechanism Zadig
    uses internally.  This works with our unsigned INF because
    ``winusb.sys`` is Microsoft-signed and already in the driver store.

    Requires Administrator (the packaged app has it via ``uac_admin``).
    Returns ``True`` if all bindings succeeded.  Safe to call multiple
    times — the binding is idempotent.
    """
    if not sys.platform.startswith("win"):
        log.warning("winusb auto-install: Windows-only, skipping on %s", sys.platform)
        return False
    try:
        from .winusb_bind import bind_winusb_silent
        return bind_winusb_silent()
    except Exception as e:
        log.warning("winusb auto-install: bind failed: %s: %s", type(e).__name__, e)
        return False


def install(dry_run: bool = False) -> int:
    """Diagnose WinUSB binding state and auto-install if possible.

    ``dry_run`` skips the silent pnputil install (parity with the
    Linux/BSD installers' dry-run mode) — only diagnoses and prints
    manual Zadig instructions for any invisible devices.
    """
    log.info("install: dry_run=%s", dry_run)
    if not _is_windows():
        log.warning("WinUSB wizard is Windows-only — current platform: %s", sys.platform)
        return 0

    if (status := _check_pyusb_backend()) != 0:
        return status

    visible, invisible = _classify_devices()

    if visible:
        print(f"\n  [OK]  {len(visible)} TRCC device(s) visible to pyusb:")
        for vid, pid, label in visible:
            print(f"          {vid:04x}:{pid:04x}  {label}")

    if not invisible:
        print("\n  All connected TRCC devices have a working USB driver.")
        return 0

    print(f"\n  [!]   {len(invisible)} TRCC device(s) need WinUSB:")
    for vid, pid, label in invisible:
        print(f"          {vid:04x}:{pid:04x}  {label}")

    # Try silent auto-install first (bundled INF + pnputil).
    if not dry_run:
        print("\n  Attempting automatic WinUSB installation...")
        if install_winusb_silent():
            print("  [OK]  WinUSB driver installed.  Re-enumerating devices...")
            # Re-check after install — device may need a re-plug, but
            # pnputil /install triggers immediate re-binding in most cases.
            visible2, invisible2 = _classify_devices()
            if not invisible2:
                print("\n  All TRCC devices now visible to pyusb.")
                return 0
            print(f"\n  {len(invisible2)} device(s) still invisible after auto-install.")
            print("  Try unplugging and replugging the device, then re-run TRCC.")
            print("  If that doesn't help, use the manual Zadig steps below.")
        else:
            print("  [X]  Automatic installation failed.  Falling back to manual setup.")

    # Manual fallback — Zadig instructions.
    print()
    print("  Manual setup with Zadig:")
    print(f"    1. Download Zadig from {_ZADIG_URL}")
    print("    2. Run as Administrator.")
    print("    3. Options -> List All Devices.")
    print("    4. Pick each device above from the dropdown.")
    print('    5. Choose "WinUSB" as the driver and click "Replace Driver".')
    print("    6. Re-run TRCC -- the handshake will succeed.")
    print()
    print("  Notes:")
    print("    - If your device is not in the dropdown, unplug + replug.")
    print("    - libusbK / libusb-win32 also work, but WinUSB is preferred.")
    print("    - Replacing a driver is reversible: Device Manager -> Uninstall.")
    return 1


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _check_pyusb_backend() -> int:
    """Verify pyusb's libusb-1.0 backend is loadable.

    Returns 0 if ready, 2 if libusb itself is missing — the WinUSB
    wizard can't tell the user what to do until pyusb can talk to the
    USB stack at all.
    """
    try:
        import usb.backend.libusb1
    except ImportError:
        print("  [X]   pyusb is not installed — pip install pyusb")
        return 2

    backend = usb.backend.libusb1.get_backend()
    if backend is None:
        print("  [X]   libusb-1.0.dll not on PATH.")
        print("        TRCC's installer normally ships it next to the .exe;")
        print("        if you're running from source, install libusb manually:")
        print("          https://libusb.info/  →  Downloads → Latest Windows Binaries")
        return 2

    return 0


def _classify_devices() -> tuple[
    list[tuple[int, int, str]], list[tuple[int, int, str]],
]:
    """Split registered devices into (visible, invisible) by VID/PID.

    "Visible" means pyusb returns at least one match.  "Invisible"
    means no match — could be unplugged OR bound to a non-libusb
    driver.  We can't tell the two apart without enumerating Windows'
    own driver tree, so the instructions cover both cases.
    """
    from ..device._pyusb_find import find as usb_find

    visible: list[tuple[int, int, str]] = []
    invisible: list[tuple[int, int, str]] = []
    for (vid, pid), product in sorted(ALL_DEVICES.items()):
        # Only check devices that need WinUSB (USB bulk / libusb access).
        # HID devices use Windows' inbox HID driver; SCSI devices use the
        # mass-storage driver -- neither needs WinUSB binding.
        if product.wire not in _WINUSB_WIRES:
            continue
        label = f"{product.vendor} {product.product}"
        if any(usb_find(find_all=True, idVendor=vid, idProduct=pid) or []):
            visible.append((vid, pid, label))
        else:
            invisible.append((vid, pid, label))
    return visible, invisible

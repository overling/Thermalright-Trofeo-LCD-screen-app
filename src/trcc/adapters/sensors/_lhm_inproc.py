"""In-process LibreHardwareMonitor sensor — read CPU temp directly from the .NET DLL.

Uses ``pythonnet`` to load ``LibreHardwareMonitorLib.dll`` in-process,
avoiding the need for WMI (removed in LHM v0.9.5+) or a REST API.
The .NET ``Computer`` object reads hardware sensors (MSR, SMBus) directly,
so this needs admin privileges but provides real CPU core temperatures
on modern CPUs that WMI-based LHM v0.9.4 couldn't read.

This source sits ahead of the WMI-based ``LhmCpu`` in the sensor chain:
when pythonnet + the DLL are available, it provides readings; otherwise
the chain falls through to WMI, ACPI, and psutil.
"""
from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path
from typing import Any

from ...core.ports import CpuSource

log = logging.getLogger(__name__)

_LHM_DLL_NAME = "LibreHardwareMonitorLib.dll"

# Search paths for the LHM library directory (DLL + dependencies).
def _lhm_lib_dir() -> Path | None:
    """Locate the directory containing ``LibreHardwareMonitorLib.dll``."""
    candidates: list[Path] = []
    # Check standalone install first — it's typically the newest version
    # with the best CPU support. Bundled lhm_nightly (v0.9.4) reports
    # 0°C on modern CPUs like the i9-14900K.
    candidates.append(Path(r"C:\trcc\lhm"))
    meipass = getattr(sys, "_MEIPASS", None)
    exe_parent = Path(sys.executable).parent
    cwd = Path.cwd()
    for base in (meipass, exe_parent, cwd):
        if base is None:
            continue
        candidates.append(Path(base) / "lhm")
        candidates.append(Path(base) / "lhm_nightly")
    for c in candidates:
        if (c / _LHM_DLL_NAME).is_file():
            return c
    return None


_computer: Any = None
_computer_lock = threading.Lock()
_computer_tried = False
_cpu_hardware: Any = None
_cpu_name: str = "LibreHardwareMonitor (in-process)"


def _init_computer() -> Any:
    """Initialize the LHM Computer object once (thread-safe).

    Returns the Computer object on success, None on failure.
    """
    global _computer, _computer_tried, _cpu_hardware, _cpu_name

    if _computer is not None:
        return _computer
    if _computer_tried:
        return None

    with _computer_lock:
        if _computer is not None:
            return _computer
        if _computer_tried:
            return None
        _computer_tried = True

        try:
            import clr  # noqa: F401  pythonnet
        except Exception as e:
            log.warning("pythonnet import failed; in-process LHM unavailable: %s", e)
            return None

        lib_dir = _lhm_lib_dir()
        if lib_dir is None:
            log.warning("LibreHardwareMonitorLib.dll not found; in-process LHM unavailable")
            return None

        log.info("LHM in-process: using library at %s", lib_dir)

        try:
            sys.path.insert(0, str(lib_dir))
            dll_path = str(lib_dir / _LHM_DLL_NAME)
            clr.AddReference(dll_path)
            from LibreHardwareMonitor import Hardware  # type: ignore[reportMissingImports]

            computer = Hardware.Computer()
            computer.IsCpuEnabled = True
            computer.IsGpuEnabled = False
            computer.IsMotherboardEnabled = False
            computer.IsStorageEnabled = False
            computer.IsBatteryEnabled = False
            computer.IsMemoryEnabled = False
            computer.IsNetworkEnabled = False
            computer.IsControllerEnabled = False
            computer.IsPsuEnabled = False
            computer.Open()
            _computer = computer
            log.info("LHM in-process: Computer.Open() succeeded (lib=%s)", lib_dir)

            # LHM needs time after Open() to initialize MSR/SMbus reading.
            # Without this delay, the first few Update() calls return None
            # for temperature and clock sensors (Load sensors work immediately
            # since they use performance counters, not MSRs).
            import time as _time
            _time.sleep(2.0)

            # Find the CPU hardware entry and do an initial update.
            for hw in computer.Hardware:
                if str(hw.HardwareType) == "Cpu":
                    _cpu_hardware = hw
                    _cpu_name = f"LHM: {hw.Name}"
                    log.info("LHM in-process: CPU found: %s", hw.Name)
                    hw.Update()
                    _time.sleep(1.0)
                    hw.Update()
                    break

        except Exception as e:
            log.warning("LHM in-process initialization failed: %s", e, exc_info=True)
            return None

        return _computer


class LhmInprocCpu(CpuSource):
    """CPU readings via in-process LHM .NET library (pythonnet).

    Reads CPU temperature, usage, frequency, and power directly from
    ``LibreHardwareMonitorLib.dll`` without spawning a subprocess or
    using WMI.  Requires admin privileges for MSR access.
    """

    def __init__(self) -> None:
        self._init_done = False

    def _ensure_init(self) -> Any:
        """Lazy-init the Computer on first read (on the poll thread)."""
        if not self._init_done:
            self._init_done = True
            _init_computer()
        return _computer

    @property
    def name(self) -> str:
        self._ensure_init()
        return _cpu_name

    def _update_and_get_cpu(self) -> Any | None:
        """Ensure Computer is initialized, update CPU hardware, return it."""
        computer = self._ensure_init()
        if computer is None:
            return None
        global _cpu_hardware
        if _cpu_hardware is None:
            for hw in computer.Hardware:
                if str(hw.HardwareType) == "Cpu":
                    _cpu_hardware = hw
                    break
        if _cpu_hardware is None:
            return None
        _cpu_hardware.Update()
        return _cpu_hardware

    def _sensors(self, sensor_type: str) -> list[Any]:
        """Return CPU sensors of the given type string."""
        cpu = self._update_and_get_cpu()
        if cpu is None:
            return []
        return [s for s in cpu.Sensors if str(s.SensorType) == sensor_type]

    def temp(self) -> float | None:
        """Hottest CPU core temperature in °C."""
        sensors = self._sensors("Temperature")
        values = [float(s.Value) for s in sensors if s.Value is not None]
        return max(values) if values else None

    def usage(self) -> float | None:
        """CPU total load 0-100."""
        sensors = self._sensors("Load")
        for s in sensors:
            if s.Value is not None and "total" in str(s.Name).lower():
                return float(s.Value)
        values = [float(s.Value) for s in sensors if s.Value is not None]
        return max(values) if values else None

    def freq(self) -> float | None:
        """Highest CPU clock in MHz."""
        sensors = self._sensors("Clock")
        values = [float(s.Value) for s in sensors if s.Value is not None]
        return max(values) if values else None

    def power(self) -> float | None:
        """Package power draw in W."""
        sensors = self._sensors("Power")
        for s in sensors:
            if s.Value is not None and "package" in str(s.Name).lower():
                return float(s.Value)
        values = [float(s.Value) for s in sensors if s.Value is not None]
        return max(values) if values else None

#!/usr/bin/env python3
"""Allow running as: python -m trcc

Sets up crash logging BEFORE any imports — ensures every OS gets
a log file at ~/.trcc/trcc.log even if the app crashes on startup.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Early logging — catches import failures, DI errors, platform issues.
# Must run before any trcc imports. All 4 OS's get a log file.
# Portable builds (PyInstaller or .trcc/ marker next to exe) keep the log
# next to the executable; non-portable dev runs use ~/.trcc/.
_exe_dir = Path(sys.executable).parent
if (
    getattr(sys, "frozen", False)
    or (_exe_dir / "trcc-user").exists()
    or (_exe_dir / ".trcc").exists()
):
    _log_dir = _exe_dir / '.trcc'
else:
    _log_dir = Path.home() / '.trcc'
_log_dir.mkdir(parents=True, exist_ok=True)
_log_path = _log_dir / 'trcc.log'


# Windows-only: stdlib RotatingFileHandler can't rotate a file that's open
# in another process — ``os.rename`` fails with WinError 32 and the default
# error path prints the traceback to stderr *and* drops the log record.
# Linux/macOS rename of an open file works, so they use the stdlib handler.
if sys.platform == 'win32':
    class _SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
        def doRollover(self) -> None:
            try:
                super().doRollover()
            except (PermissionError, OSError):
                pass

    _rotating_handler_cls: type[logging.handlers.RotatingFileHandler] = _SafeRotatingFileHandler
else:
    _rotating_handler_cls = logging.handlers.RotatingFileHandler


_early_handler = _rotating_handler_cls(
    _log_path, maxBytes=1_000_000, backupCount=3,
    encoding='utf-8', errors='replace',
)
# Tag the early shim so ``adapters.infra.logging.configure_logging`` knows
# to swap it out when it runs.  Without the tag, both handlers stay
# attached and every log line gets written twice.
_early_handler._trcc_handler = True  # type: ignore[attr-defined]
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[_early_handler],
)
log = logging.getLogger('trcc.main')
log.info("Starting TRCC — platform=%s, executable=%s", sys.platform, sys.executable)

# Windows: stdout/stderr default to cp1252, which can't encode common
# Unicode chars used in log messages (e.g. ``→``, ``°``).  ``reconfigure``
# is a silent no-op on some Python deployments (Windows Store), so on
# top of that we monkey-patch ``logging.StreamHandler.emit`` to wrap the
# write call in its own ``except UnicodeEncodeError`` that re-encodes
# with ``errors='replace'``.  This catches EVERY StreamHandler — ours,
# stdlib lastResort, third-party — at the class level, no matter when
# or where they're instantiated.
if sys.platform == 'win32':
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            try:
                _stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, OSError, ValueError):
                pass

    def _safe_stream_emit(self: logging.StreamHandler, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                encoding = getattr(stream, 'encoding', 'ascii') or 'ascii'
                safe = msg.encode(encoding, errors='replace').decode(encoding)
                stream.write(safe + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    logging.StreamHandler.emit = _safe_stream_emit  # type: ignore[method-assign]

# Windows: ensure libusb-1.0.dll is findable by pyusb (ctypes).
# PyInstaller bundles the DLL next to the exe, but Python 3.8+ on Windows
# doesn't search the exe's directory for ctypes DLLs unless explicitly told.
# Without this, pyusb raises ``NoBackendError: No backend available``.
if sys.platform == 'win32':
    _app_dir = Path(sys.executable).parent
    try:
        os.add_dll_directory(str(_app_dir))
        log.debug("Added DLL search directory: %s", _app_dir)
    except (OSError, AttributeError):
        pass  # add_dll_directory requires Python 3.8+ and a valid dir

    # Auto-install the bundled WinUSB INF so pyusb can talk to TRCC's
    # bulk/LY LCD devices without the user manually running Zadig.
    # Idempotent: pnputil skips already-installed INFs.  Runs only on
    # Windows + only if the bundled INF is present + only at startup
    # (so the driver is bound before any device enumeration).
    # User consent: prompt on first run (when no consent flag exists).
    # Subsequent runs skip the prompt and re-bind silently.
    try:
        import ctypes
        from trcc.adapters.system._winusb import install_winusb_silent

        _consent_flag = _app_dir / ".trcc" / "winusb_consent.txt"
        # _consent_state: None = never asked, "granted" = yes, "declined" = no
        _consent_state = None
        if _consent_flag.exists():
            try:
                _consent_state = _consent_flag.read_text(encoding="utf-8").strip()
            except Exception:
                _consent_state = None

        _proceed = False
        if _consent_state == "granted":
            _proceed = True
        elif _consent_state == "declined":
            _proceed = False
        else:
            # First run — check if any TRCC bulk/LY device is present
            # before prompting (no point asking if nothing to bind).
            _should_ask = False
            try:
                from trcc.adapters.system._winusb import _classify_devices
                _visible, _invisible = _classify_devices()
                _should_ask = bool(_visible or _invisible)
            except Exception:
                _should_ask = True  # If check fails, ask anyway

            if _should_ask:
                _MB_YESNO = 0x04
                _MB_ICONQUESTION = 0x20
                _MB_DEFBUTTON1 = 0x000
                _IDYES = 6
                _title = "TRCC - Driver Setup"
                _msg = (
                    "TRCC needs to bind the WinUSB driver to your LCD cooler(s) "
                    "so it can communicate with them.\n\n"
                    "This is a one-time setup and requires administrator "
                    "privileges (which you already granted to launch TRCC).\n\n"
                    "Click Yes to proceed, or No to skip (you can install "
                    "the driver manually later via Zadig if needed)."
                )
                try:
                    _rc = ctypes.windll.user32.MessageBoxW(
                        0, _msg, _title,
                        _MB_YESNO | _MB_ICONQUESTION | _MB_DEFBUTTON1)
                except Exception:
                    _rc = _IDYES  # If MessageBox fails, proceed silently
                _proceed = (_rc == _IDYES)
                # Record consent so we don't prompt again on every launch
                try:
                    _consent_flag.parent.mkdir(parents=True, exist_ok=True)
                    _consent_flag.write_text(
                        "granted\n" if _proceed else "declined\n",
                        encoding="utf-8")
                except Exception:
                    pass
                if not _proceed:
                    log.info("WinUSB auto-install: user declined consent")

        if _proceed:
            if install_winusb_silent():
                log.info("WinUSB: bundled INF installed successfully")
            # Failure is non-fatal -- device recovery / system setup wizard
            # will surface the manual Zadig instructions if needed.
    except Exception as e:
        log.debug("WinUSB auto-install skipped: %s: %s", type(e).__name__, e)

try:
    # Auto-launch GUI when invoked as trcc-gui.exe (windowed PyInstaller build)
    if Path(sys.executable).name.lower().startswith('trcc-gui'):
        from trcc.ui.cli.main import gui
        sys.exit(gui() or 0)
    # Everything else goes through the shared entry so python -m trcc and
    # the `trcc` console script dispatch the same way.
    from trcc._entry import main
    sys.exit(main() or 0)
except Exception:
    log.critical("Fatal startup error", exc_info=True)
    raise

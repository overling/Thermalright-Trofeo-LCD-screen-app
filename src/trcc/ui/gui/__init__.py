"""GUI composition root for next/ — wires Qt adapter.

Single entry point for the graphical interface.  Builds the windowed
``QApplication`` (which Qt requires before any QWidget), constructs an
``App`` via ``trcc._boot.trcc()``, then hands the app handle
to ``MainWindow``.  ``discover`` runs in a background ``BootstrapWorker``
so the splash shows immediate feedback.

Composition root — this is the ONE place that imports concrete adapters
(``Platform``, ``QtRenderer``, ``IPCServer``, ``SingleInstance``).  Every
other file under ``next/ui/gui/`` holds an ``App`` handle and dispatches
Commands.
"""
from __future__ import annotations

import logging
import signal
import sys
from collections.abc import Callable
from typing import Any

from .base import BasePanel, ImageLabel
from .trcc_app import TRCCApp
from .uc_device import UCDevice
from .uc_preview import UCPreview
from .uc_theme_local import UCThemeLocal
from .uc_theme_mask import UCThemeMask
from .uc_theme_setting import UCThemeSetting
from .uc_theme_web import UCThemeWeb

__all__ = [
    'BasePanel',
    'ImageLabel',
    'TRCCApp',
    'UCDevice',
    'UCPreview',
    'UCThemeLocal',
    'UCThemeMask',
    'UCThemeSetting',
    'UCThemeWeb',
    'launch',
    'run_gui',
]

log = logging.getLogger(__name__)


def launch(verbosity: int = 0, decorated: bool = False,
           start_hidden: bool = False) -> int:
    """Bootstrap and run the shipping GUI.  Returns the Qt exit code.

    Thin wrapper over :func:`run_gui` — builds the real host platform and
    runs the full composition with the production seams on (single-instance
    lock, IPC server, ``os._exit`` reap).

    ``verbosity`` is unused: the CLI root callback (``ui.cli.main:_root``)
    ALWAYS runs first and has already configured logging at the requested
    level.  Re-configuring here would silently downgrade DEBUG back to INFO.
    """
    del verbosity
    from ...adapters.system import PlatformFactory
    platform = PlatformFactory.current()
    return run(platform, decorated=decorated, start_hidden=start_hidden)


def run(platform: Any, *, decorated: bool = False,
        start_hidden: bool = False, single_instance: bool = True,
        ipc: bool = True, force_exit: bool = True,
        on_ready: Callable[[Any], None] | None = None) -> int:
    """Run the GUI composition from an injected ``platform``.  Returns exit code.

    The GUI's ``run(platform, …)`` in the unified UI-launch contract (see
    ``METHOD_UI.md``): the composition root injects the ``Platform`` port and
    this UI composes its App from it (Qt-first, via ``build_qt_app``).  It takes
    a platform rather than a pre-built App because the windowed ``QApplication``
    must precede ``QtRenderer`` and the single-instance early-return must precede
    any build — constraints App-injection can't satisfy.

    The ONE shared composition root for every GUI entry point — shipping
    ``launch`` and ``dev/mock_gui`` both call this, so the dev mock exercises
    the SAME code the real app runs (the whole reason to mock: real code
    paths surface real bugs).  Callers differ only in what ``platform`` they
    build and these seams:

      * ``single_instance`` — acquire the cross-process GUI lock (off for the
        dev mock so it never collides with a real install).
      * ``ipc`` — bind the daemon-style IPC server (off for the dev mock to
        avoid socket collision).
      * ``force_exit`` — ``os._exit`` to reap native threads (psutil / pyusb /
        pynvml can outlive ``qapp.exec()``); the dev mock returns normally.

    Logging is NOT configured here — that stays the caller's job (CLI root
    callback for shipping, ``dev/_mock_bootstrap`` for the mock), so the
    "configure_logging exactly once" invariant holds.
    """
    from typing import cast

    from PySide6.QtWidgets import QApplication

    # ── stdout/stderr UTF-8 (Windows cp1252 fix; no-op elsewhere) ────
    platform.configure_stdout()

    # ── Single-instance lock + raise-existing-window ─────────────────
    instance = None
    if single_instance:
        from ...ipc import SingleInstance
        instance = SingleInstance("gui")
        if instance is None:
            # A peer GUI was already running; raise was sent.  Exit cleanly.
            return 0

    # ── Assets dir (packaged location) ───────────────────────────────
    from .assets import _PKG_ASSETS_DIR, set_assets_dir
    set_assets_dir(_PKG_ASSETS_DIR)

    # ── Qt bootstrap + App (QApplication precedes QtRenderer) ──────
    # The shared Qt-first composition, identical to the qtgui skin: set the Qt
    # env, build the windowed QApplication, apply the shared QApp settings, then
    # build the App via the canonical factory with a QtRenderer.  (build_qt_app)
    #
    # NOTE: we inline build_qt_app here rather than calling it because the
    # legacy GUI's DPI/scale compensation MUST run between QApplication
    # construction and App composition: it mutates the ``Layout`` / ``Sizes``
    # constant classes (and the ``core.i18n`` font tuples) in place so every
    # widget built afterwards picks up the scaled geometry.  Calling
    # ``build_qt_app`` would build the App (and its widgets) before we had a
    # chance to scale, producing the half-black / clipped / tiny-text window
    # seen when this block was accidentally dropped.
    from ..qapp import configure_qt_environment, configure_qapplication
    configure_qt_environment()
    qapp = QApplication.instance()
    if not isinstance(qapp, QApplication):
        qapp = QApplication(sys.argv)
    # NOTE: configure_qapplication is called AFTER DPI scale is computed
    # so the global font can be scaled to match.

    # ── DPI / available-geometry scaling ────────────────────────────
    # The process is declared PerMonitorV2 DPI-aware in the exe manifest
    # (trcc.manifest), and QT_ENABLE_HIGHDPI_SCALING=0 is set in
    # configure_qt_environment so Qt uses logical = physical coordinates
    # (dpr=1.0).  The baked Layout/Sizes constants are designed for 96-DPI
    # 1454x800; we manually scale them by (screen DPI / 96) so the window
    # occupies the right physical area on high-DPI screens.  This matches
    # the original working build's approach.
    from .constants import Layout, Sizes
    _screen = qapp.primaryScreen()
    if _screen is not None:
        _dpi = int(_screen.logicalDotsPerInch())
        _dpr = _screen.devicePixelRatio()
        _scale = _dpi / 96.0
        _avail = _screen.availableGeometry()
        _max_scale = min(_avail.width() / Sizes.WINDOW_W,
                         _avail.height() / Sizes.WINDOW_H)
        # Cap at 1.75x so the app fills most of a 4K display without
        # overflowing (2.0x fills the entire screen which is too large).
        _scale = min(_scale, _max_scale, 1.75)
        if _scale < 1.0:
            _scale = 1.0
        # In Qt 6, HighDPI scaling is always enabled.  When dpr > 1.0,
        # Qt scales widget coordinates by dpr automatically.  Our manual
        # scaling would compound with Qt's, producing windows that are
        # _scale * _dpr times too large (or clamped to a tiny size).
        # To compensate, divide our manual scale by dpr so the net
        # effect is just Qt's dpr scaling (which produces crisp text).
        if _dpr > 1.0:
            _scale = _scale / _dpr
            if _scale < 1.0:
                _scale = 1.0
        # Fit-to-screen may legitimately require <1.0.  The floors above
        # only prevent the DPI math from *shrinking* the UI; they must
        # not block fitting a screen smaller than the 1454x800 design
        # (e.g. 1440p @ 200% scaling = 1280x720 logical).  Without this
        # the window is larger than the display and widgets get clipped.
        if _max_scale < 1.0:
            _scale = max(_max_scale, 0.5)
        log.info("run: screen=%s dpi=%d dpr=%.2f scale=%.2f max_scale=%.2f avail=%dx%d",
                 _screen.name(), _dpi, _dpr,
                 _scale, _max_scale,
                 _avail.width(), _avail.height())
        # Counts / name-lengths — scaling them would corrupt the grid.
        _no_scale = frozenset({
            'THUMB_NAME_MAX', 'THUMB_NAME_TRUNC',
            'OVERLAY_COLS', 'OVERLAY_ROWS', 'GRID_COLS',
        })
        for _cls in (Layout, Sizes):
            for _attr in list(vars(_cls).keys()):
                if _attr in _no_scale:
                    continue
                _val = getattr(_cls, _attr)
                if isinstance(_val, tuple) and all(
                        isinstance(v, (int, float)) and not isinstance(v, bool)
                        for v in _val):
                    setattr(_cls, _attr, tuple(int(v * _scale) for v in _val))
                elif isinstance(_val, (int, float)) and not isinstance(_val, bool):
                    setattr(_cls, _attr, int(_val * _scale))
        log.info("run: after scale Sizes.WINDOW_W=%d Sizes.WINDOW_H=%d",
                 Sizes.WINDOW_W, Sizes.WINDOW_H)
        # core.i18n font tuples are (x, y, w, h, pt) — scale geometry and
        # point size together so localized labels stay proportional.
        from ...core import i18n as _i18n_module
        for _attr in list(vars(_i18n_module).keys()):
            if not _attr.startswith('_'):
                _val = getattr(_i18n_module, _attr)
                if (isinstance(_val, tuple) and len(_val) == 5
                        and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                for v in _val)):
                    x, y, w, h, pt = _val
                    setattr(_i18n_module, _attr,
                            (int(x * _scale), int(y * _scale),
                             int(w * _scale), int(h * _scale),
                             int(pt * _scale)))

    # Now apply the scaled global font
    configure_qapplication(qapp, font_scale=_scale)

    # ── App composition (QtRenderer needs the QApplication above) ──
    from ..._boot import trcc
    from ...adapters.render.qt import QtRenderer
    app = trcc(platform=platform, renderer=QtRenderer())

    # ── "Minimize on startup" toggle — overrides start_hidden if the
    # user enabled it in the GUI.  Reads from the persisted trcc.json
    # so the boot-launched exe hides to the tray without showing a window.
    if not start_hidden and getattr(app.settings, "start_minimized", False):
        log.info("run: start_minimized=True in settings — hiding to tray")
        start_hidden = True

    # ── Splash + background discover ────────────────────────────────
    from .splash import run_bootstrap_with_splash
    if not run_bootstrap_with_splash(app):
        return 1

    # ── Hotplug listener + metrics broadcast (one cadence drives the
    # system-info / activity sidebar / overlay refresh) ─────────────
    app.start_hotplug()
    app.metrics_loop.start()
    # Fast LED effect/carousel animation (breathing/colour-cycle/rainbow) —
    # the slow sensor cadence can't animate them.
    app.led_animation_loop.start()

    # ── Main window — TRCCApp keeps the legacy chrome ──────────────
    window = TRCCApp(app=app, decorated=decorated)

    # ── IPC server bound to App — daemon-style Command dispatch ─────
    ipc_server = None
    if ipc:
        from ...ipc import IPCServer
        ipc_server = IPCServer(app=app)
        ipc_server.start()
        window._ipc_server = ipc_server

    # ── Wire raise-existing-window callback ─────────────────────────
    # SingleInstance invokes this from its accept thread; emitting the Qt
    # signal is thread-safe and the QueuedConnection marshals the window
    # show/raise onto the GUI main thread (#196 — a direct cross-thread
    # QWidget call deadlocked the event loop).
    if instance is not None:
        instance.on_raise = window.raise_requested.emit

    # ── Initial device replay — discover ran in the splash worker, so
    # iterate ``app.devices`` once for the first sidebar render.  Live
    # mutations after this come through DeviceConnected/Disconnected.
    window.replay_initial_devices()

    # Optional post-build hook — a behaviour-neutral extension point (default
    # None).  The dev mock GUI uses it to mount its developer console; shipping
    # callers pass nothing.
    if on_ready is not None:
        on_ready(window)

    def _on_quit_signal(*_args: object) -> None:
        """SIGINT / SIGTERM — quit the Qt event loop cleanly.

        SIGTERM is what the session manager / systemd sends at PC shutdown;
        without it the process is killed before ``qapp.exec()`` returns, so
        the ``finally`` cleanup (``app.close()`` → device disconnect) never
        runs and the LCD is left mid-stream showing "USB communication lost"
        (#143).  The handler fires promptly because the metrics/render
        QTimers keep yielding to the interpreter between Qt events.
        """
        qapp.quit()
    signal.signal(signal.SIGINT, _on_quit_signal)
    signal.signal(signal.SIGTERM, _on_quit_signal)

    if not start_hidden:
        window.show()
        # Surface any device that was found but didn't connect — with the
        # OS-correct hint the Platform supplied (e.g. "run as administrator").
        # Read from the bus (DeviceConnectionIssues query), NOT a handed list:
        # the failures fired before the window subscribed, so we pull them
        # from the App model the bus-pure way.  Live failures arrive via the
        # ErrorOccurred subscription wired in the window.
        from ...core.commands import DeviceConnectionIssues
        window.notify_device_failures(
            app.dispatch(DeviceConnectionIssues()).issues,
        )

    try:
        exit_code = qapp.exec()
    finally:
        if ipc_server is not None:
            ipc_server.shutdown()
        if instance is not None:
            instance.close()
        app.close()
        log.info("run_gui: cleanup complete — process exit")

    # Belt-and-suspenders: Qt's metrics/sensor/render threads occasionally
    # outlive ``qapp.exec()``'s return when native libraries (pynvml,
    # psutil's ffi handles, pyusb) hold the GIL on shutdown.  ``os._exit``
    # skips atexit handlers and finalizers — we already did our cleanup in
    # the finally above, so this is the safe place to force the kernel to
    # reap the process.  The dev mock returns normally (``force_exit=False``).
    if force_exit:
        import os as _os
        _os._exit(exit_code)
    return exit_code


# Back-compat alias — ``dev/mock_gui`` and existing tests call ``run_gui``.
# ``run`` is the canonical name in the unified UI-launch contract.
run_gui = run

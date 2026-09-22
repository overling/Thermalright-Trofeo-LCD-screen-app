# TRCC — Complete Knowledge Base

## 1. Project Overview

TRCC (Thermalright LCD/LED Cooler Control) is a cross-platform desktop application
for controlling Thermalright LCD display panels and RGB LED controllers. It is a
Python rewrite of the original Windows C# application (TRCC.cs), preserving
byte-level protocol parity while adding Linux, macOS, and BSD support.

- **Package name**: `trcc-linux` (PyPI), version 9.9.2
- **License**: GPL-3.0-or-later
- **Python**: >=3.10
- **GUI framework**: PySide6 (Qt 6)
- **Source**: `C:\trcc-src\` (src layout: `src/trcc/`)
- **Deployed**: `C:\trcc\dist\trcc-gui\`
- **Build tool**: PyInstaller (`trcc-gui.spec`, `TRCC.spec`)
- **Repo**: `github.com/Lexonight1/thermalright-trcc-linux`
- **Design size**: 1454x800 logical pixels (GUI), 200% DPI → 2908x1600 physical
- **Window title**: `TRCC-Linux - Thermalright LCD Control Center`
- **Font**: Microsoft YaHei, base 10pt

### Supported Device Families

| Wire Protocol | Kind | Example Products | Native Resolution |
|---|---|---|---|
| SCSI | LCD | Thermalright LCD Display | 320x320 |
| HID | LCD | Winbond USBDISPLAY (Type 2/3) | 240x320, 320x320 |
| BULK | LCD | GrandVision 360 AIO | 480x480 |
| BULK_ALI | LCD | Elite Vision 360 ARGB (ALi variant) | 320x320 |
| LY | LCD | Trofeo Vision 9.16 | 1920x462 |
| LED | LED | Winbond LED Controller | N/A |

Volatile frame wires (Bulk, Bulk_Ali, LY) require keepalive resends (~150ms)
or the firmware reverts to the built-in logo. SCSI/HID latch the last frame.

---

## 2. Architecture — Hexagonal (Ports & Adapters)

TRCC follows a strict hexagonal architecture. The dependency rule is:
**UI → Commands → App → Ports (ABCs) ← Adapters**. Core never imports adapters;
UI never imports adapters directly (enforced by ruff TID251 banned-api rule).

```
┌─────────────────────────────────────────────────────────┐
│                        UI Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ GUI      │  │ CLI      │  │ REST API │               │
│  │ (PySide6)│  │ (Typer)  │  │(FastAPI) │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │                     │
│       └──────────────┼──────────────┘                     │
│                      ▼                                    │
│              Command Bus (dispatch)                       │
│                      │                                    │
├──────────────────────┼────────────────────────────────────┤
│                      ▼                                    │
│                   App (hub)                               │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Settings · Themes · Media · Overlay · Display ·     │ │
│  │ MetricsLoop · LedAnimationLoop · CloudTheme ·       │ │
│  │ DataInstall · Slideshow · Quickstart · Diagnostics  │ │
│  └─────────────────────────────────────────────────────┘ │
│                      │                                    │
│              Ports (ABCs in core/ports.py)                │
│  Platform · Device · Renderer · Sensors · Paths ·        │
│  Diagnostics · CloudCatalog · SendScheduler · …          │
│                      │                                    │
├──────────────────────┼────────────────────────────────────┤
│                      ▼                                    │
│                 Adapters Layer                            │
│  system/{windows,linux,macos,bsd} · device/{scsi,hid,    │
│  bulk,bulk_ali,ly,led} · sensors/{psutil,nvml,wmi,…} ·   │
│  repo/{github_releases,http,data_install} · theme/cloud  │
│  infra/{logging,send_scheduler,sysinfo_config}           │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

- **Core** (`core/`): Pure domain — models, enums, ports (ABCs), commands,
  events, results, errors, protocol, registry, geometry, i18n, variants.
  No I/O, no Qt, no adapter imports.
- **Services** (`services/`): Application logic that orchestrates ports.
  Settings, DisplayService, OverlayService, MediaService, ThemeService,
  MetricsLoop, LedAnimationLoop, LEDEffectEngine, CloudThemeService,
  DataInstallService, SlideshowService, DeviceSender, QuickstartService.
- **Adapters** (`adapters/`): OS/device/protocol implementations of ports.
  system/ (platform), device/ (USB transports), sensors/ (hardware readers),
  repo/ (HTTP + data install), theme/ (cloud catalog), infra/ (logging,
  send scheduler, sysinfo config).
- **UI** (`ui/`): Three frontends — GUI (PySide6), CLI (Typer), API (FastAPI).
  All dispatch Commands through `app.dispatch(cmd)`; none touch devices directly.

### Key Architectural Rules

1. **UI cannot import `trcc.adapters.device`** — enforced by ruff TID251.
   UI must use `trcc.lcd` / `trcc.led` / `trcc.probe` / `trcc.handshake`.
2. **Commands are the universal API** — every user action is a Command object
   dispatched through `app.dispatch(cmd)`, returning a typed `Result`.
3. **EventBus is synchronous** — adapters bridge to async (Qt signals for GUI,
   SSE/WebSocket for API). Handlers are called inline on publish.
4. **PlatformFactory** is the OCP chokepoint — a new OS adds one file under
   `adapters/system/` with `@PlatformFactory.register("os_name")`.
5. **Device registry is data-driven** — adding a device = append a row to
   `ALL_DEVICES` in `registry.py`. Zero code changes elsewhere.

---

## 3. Core Layer (`src/trcc/core/`)

### `models.py` (1286 lines)
Frozen dataclasses + enums. No logic, no I/O.
- `Wire` enum: SCSI, HID, BULK, BULK_ALI, LY, LED
- `Kind` enum: LCD, LED
- `Capability` enum: FRAME_RENDER, COLOR_FILL, BRIGHTNESS, OVERLAY, MASK,
  ORIENTATION, EFFECTS, LED_ZONES
- `VOLATILE_FRAME_WIRES`: frozenset of wires needing keepalive resends
- `ProductInfo`: (vid, pid, vendor, product, wire, kind, native_resolution,
  orientations, fbl, device_type, model, button_image)
- `DeviceSettings`: per-device prefs (orientation, brightness, theme path,
  overlay enabled, temp_unit, time_format, date_format, fit_mode, split_mode,
  background, slideshow config)
- `Theme`: loaded theme metadata (path, config, elements, mask, fonts)
- `OverlayElement`: one overlay text/metric element (id, type, sensor_id,
  position, font, color, format)
- `HardwareMetrics`: typed sensor snapshot (cpu_temp, gpu_temp, memory, etc.)
- `SensorReading`: one sensor's value + metadata
- `oriented_resolution()`: swaps W/H for portrait orientations
- `LedStyle`: enum of LED controller hardware styles

### `ports.py` (1472 lines)
ABCs that adapters implement. Key ports:
- `Platform`: the OS — provides `paths()`, `sensors()`, `open()`, `hotplug()`,
  `configure_stdout()`, `check_permissions()`, `power_events()`
- `Device`: one connected USB device — `connect()`, `send()`, `disconnect()`,
  `profile`, `product_info`
- `Renderer`: composites frames (bg + overlay → surface)
- `SensorEnumerator`: reads OS sensors (CPU/GPU temp, fan, memory, disk)
- `Paths`: all filesystem paths (config dir, log file, theme dirs, user data)
- `Diagnostics`: health checks, doctor, debug report, GPU reader state
- `CloudCatalog`: lists/fetches cloud themes
- `SendScheduler`: drives `SendTask` instances (thread-per-device in production)
- `BulkTransport` / `ScsiTransport`: raw USB byte movers

### `commands/` (Command bus)
`_base.py`: `Command(ABC, Generic[R_co])` — one `execute(app) -> Result` method.
`LOG_LEVEL` classvar controls dispatch logging verbosity.

Commands are organized into four modules:
- **`device.py`**: ConnectDevice, DisconnectDevice, DiscoverDevices,
  SendFrame, SendColor, SendImage, RenderAndSend, SetBrightness, SetOrientation,
  SetFitMode, SetBackground, PlayVideo, StopVideo, StartScreencast, StopScreencast,
  ApplyMask, EnableOverlay, AddOverlayElement, UpdateOverlayElement, etc.
- **`theme.py`**: LoadTheme, RestoreLastTheme, SaveTheme, ExportTheme, ImportTheme,
  ListThemes, ListCloudThemes, LoadCloudTheme, LoadImage, LoadVideo,
  UploadCustomMask, EnsureDataDownload, etc.
- **`led.py`**: InitializeLed, RenderLed, SetLedMode, SetLedColor, SetLedBrightness,
  SetLedZoneColor, SetLedZoneMode, ToggleLed, ToggleSegment, SelectZone,
  SetClockFormat, SetHddEnabled, SetMemoryRatio, etc.
- **`system.py`**: SetLanguage, SetTempUnit, SetRefreshInterval, SetGpuDevice,
  RunDoctor, RunHealthCheck, RunQuickstart, RunSetup, CheckForUpdate,
  GenerateDebugReport, EnableAutostart, DisableAutostart, ListSensors,
  ListGpus, ListDisks, ListLanguages, etc.

### `events.py` (418 lines)
`EventBus` + frozen `Event` dataclasses. Synchronous fan-out.
Key events: DeviceDiscovered, DeviceConnected, DeviceDisconnected, FrameSent,
OrientationChanged, BrightnessChanged, OverlayChanged, ThemeLoaded, VideoStarted,
VideoStopped, ScreencastStarted, SensorsUpdated, ErrorOccurred, DeviceAttached,
DeviceDetached, SystemSuspending, SystemResumed, TempUnitChanged, etc.

`SensorsUpdated` carries the personalized readings dict + typed `HardwareMetrics`
snapshot. Read-only contract — subscribers must not mutate the shared dict.

### `protocol.py` (374 lines)
`DeviceProfile` — everything derivable from an FBL code: resolution, encoding
(JPEG vs RGB565), byte order, pre-rotate flag, widescreen flag, encode baseline.
FBL byte comes from handshake. PM byte disambiguates shared FBL codes
(FBL 192 → multiple resolutions via `_FBL_192_BY_PM`).

### `registry.py` (177 lines)
`ALL_DEVICES: dict[(vid, pid), ProductInfo]` — the hardware registry.
Adding a device = append a row. Lookup: `find_product(vid, pid)`.

### `variants.py` (237 lines)
Per-(PM, SUB) variant overrides applied post-handshake. One (VID, PID) can
ship as multiple physical products; the handshake fingerprint distinguishes them.
Overrides: button_image, panel_cutout, display_name.

### `geometry.py` (162 lines)
Pure orientation geometry decisions. `content_is_portrait()` and `plan_orientation()`
resolve whether content is portrait-oriented and what rotation to apply.
Portrait = folder switch (theme{w}{h} → theme{h}{w}), not a pixel spin.

### `results.py` (754 lines)
Frozen Result dataclasses returned by Commands. Every Command has one
concrete Result type. Base: `Result(ok, message)`. Subclasses: DiscoverResult,
ConnectResult, SendResult, RenderResult, SensorInfoResult, ThemeListResult, etc.

### `errors.py` (66 lines)
Domain exception hierarchy: `TrccError` base → DeviceNotFoundError,
DeviceNotConnectedError, HandshakeError, TransportError, DeviceDisconnectedError,
PermissionError_, UnsupportedOperationError, ConfigError, ThemeError.
`HttpFetchError` subclasses `RuntimeError` deliberately (not swallowed by
`except TrccError` handlers).

### `i18n.py` (2207 lines)
38 language codes (ISO 639-1). `TRANSLATIONS[lang][english_key] -> translated`.
`tr()` falls back to English, then to the key itself. `LANGUAGE_NAMES` maps
codes to native spellings for language pickers.

### `led_models.py` (403 lines)
`LEDMode` IntEnum: STATIC, BREATHING, COLORFUL, RAINBOW, TEMP_LINKED, LOAD_LINKED.
`LedZoneSettings`: per-zone mode/color/brightness/on. `LedDeviceSettings`:
persisted LED prefs (mode, color, brightness, zones, zone_sync, test_mode,
temp_source, load_source, segment_on, clock_24h, memory_ratio, disk_index).
`LedRuntimeState`: transient tick counters (rgb_timer, test_timer, zone_sync).
`LedPayload`: structured send() shape (colors + global_on).

### Other core files
- `_colors.py`: color utility functions
- `_safe.py`: safe JSON loading, zip member validation
- `_version.py`: version string
- `device_recovery.py`: consecutive-failure tracking + auto-disconnect
- `diagnostics.py`: HealthCheckResult, HealthReport, DoctorResult DTOs

---

## 4. Services Layer (`src/trcc/services/`)

### `settings.py` (865 lines)
User preferences persisted to `trcc.json`. Two layers:
- `AppSettings`: global (language, refresh_interval, active_device, temp_unit,
  time_format, date_format, active_gpu, start_minimized, hdd_enabled, ui_theme)
- `DeviceSettings` (in core/models.py): per-device (orientation, brightness,
  theme, overlay, fit_mode, background, slideshow)

Thread-safe (RLock). Atomic save (write tmp → fsync → rename). Missing/corrupt
config falls back to defaults. Pre-cutover filename `trcc-next.json` read as
fallback for migration. `_save()` only called by mutator methods (user actions).

### `display.py` (1379 lines)
DisplayService — cached two-layer render pipeline:
1. **bg_mask**: fitted background (image or video frame) composited with mask.
   Rebuilt only on theme/orientation/video-cursor change.
2. **overlay**: transparent layer with metric/static text. Rebuilt only on
   sensor value or theme config change.
Per-tick: blend caches → dim for brightness → rotate → encode for wire.
Order mirrors C# ground truth: fit → overlay → dim → rotate → encode.

### `overlay.py` (383 lines)
OverlayService — text/metric overlays composited on a background.
`resolve_overlay_elements()`: precedence is user_elements > mask_elements >
theme_elements. Each REPLACES, never adds (prevents double-drawing bug).

### `theme.py` (835 lines)
ThemeService — theme discovery and metadata parsing.
A theme is a directory with `trcc.json` (element layout), `background.png`,
and optional mask images, animation frames, fonts.
Config resolution: `trcc.json` (native) > `trcc-next.json` (pre-cutover) >
`config1.dc` (binary legacy, read-only, auto-migrated).

### `media.py` (480 lines)
MediaService — video decoding + playback state.
`VideoDecoder`: ffmpeg → raw RGB24 frames (in-memory, no disk temp files).
`ZtDecoder`: Thermalright `.zt` animation archives (JPEG sequence + timestamps).
Playback state: current frame, cursor, fps.

### `metrics_loop.py` (253 lines)
MetricsLoop — daemon thread that polls OS sensors every `refresh_interval_s`
and publishes `SensorsUpdated` on the EventBus. Reads settings per iteration
so changes take effect on next sleep. Not auto-started; caller (GUI, daemon)
calls `app.metrics_loop.start()`.

### `led_animation_loop.py`
LedAnimationLoop — fast (~150ms) LED effect/carousel animation tick.
Separate from the slow sensor broadcast. Breathing/color-cycle/rainbow/carousel
need this cadence to actually animate. Opt-in start like metrics_loop.

### `led_effects.py` (533 lines)
LEDEffectEngine — per-segment RGB color computation per tick.
Pure computation: reads `LedDeviceSettings` + `LedRuntimeState` + sensor snapshot,
advances counters, returns logical color array. Global brightness baked in here
(single writer) so wire and preview show identical colors.

### `device_sender.py` (249 lines)
DeviceSender — per-device send worker (actor). Serializes all writes to one
device. Keepalive-resends last frame on volatile wires (Bulk/LY) every ~150ms.
Pure policy (SendTask) driven by a SendScheduler (thread-per-device in production).

### `cloud_theme.py` (188 lines)
CloudThemeService — downloads cloud video themes and stages them as backgrounds.
A cloud theme is just a background MP4; picking one swaps the device background
without touching theme/mask/overlay.

### `data_install.py` (103 lines)
DataInstallService — per-resolution data archive installation (themes, web,
masks). Idempotent — only writes if data not already present.

### `slideshow.py` (106 lines)
SlideshowService — rotate through a list of themes on a timer.
Per-device cursor advanced by the render tick. No background thread.

### `first_run.py` (81 lines)
FirstRunService — `.first-run-done` marker file. `mark_completed()` writes once;
not written on every startup after initial run.

### `migration.py`
LibraryMigration — one-time directory layout migration. Idempotent, swallows
I/O errors, can't block startup.

### `quickstart.py`
QuickstartService — guided first-session orchestrator. Sequences doctor + scan.

### `metrics_personalize.py`
Personalizes sensor readings: temp unit conversion (°C → °F), HDD filtering,
per-user metric selection.

### `video_cache.py`
VideoFrameCache — per-video frame cache for the render pipeline.

### `video_export.py`
Video export utilities.

### `audio.py`
Audio spectrum visualizer overlay for screencast capture.

### `_dc.py`
Binary `config1.dc` theme config parser (legacy format, read-only).

### `_clock.py`
Clock/date formatting utilities for overlay rendering.

### `_ansi.py`
ANSI color codes for CLI output.

---

## 5. Adapters Layer (`src/trcc/adapters/`)

### `system/` — Platform implementations
- `__init__.py`: `PlatformFactory` registry + dispatch. `current()` returns
  the Platform matching `sys.platform`.
- `windows.py`: Windows Platform (WMI, WinUSB, pywin32)
- `_winusb.py`: WinUSB driver binding for USB device access
- `_windows_wmi.py`: WMI-based sensor readings (CPU temp, etc.)
- `_hotplug.py`: Device attach/detach monitoring
- `_autostart.py`: OS-specific autostart (registry on Windows, .desktop on Linux)
- `_elevate.py`: UAC elevation for admin privileges
- `_imc_timings.py`: MCHBAR memory timing reader (privileged)
- `spd.py`: SPD memory module reader

### `device/` — USB device transports
Implements `Device` port for each wire protocol:
- SCSI (USB mass-storage passthrough)
- HID (64-byte reports)
- BULK (raw USB bulk endpoints)
- BULK_ALI (ALi variant, distinct protocol)
- LY (Trofeo Vision ultrawide)
- LED (HID 64-byte reports, RGB controller)

`DeviceFactory` dispatches to the right subclass based on `ProductInfo.wire`.

### `sensors/` — OS sensor readers
- `psutil_sources.py`: CPU/GPU temp, load, memory, disk, network (cross-platform)
- `nvml.py`: NVIDIA GPU temp/usage/clock via NVML
- `gpu_detect.py`: GPU detection and enumeration
- `windows.py`: Windows-specific sensors (WMI-backed)
- `macos.py`: macOS-specific sensors
- `bsd.py`: BSD-specific sensors
- `chain.py`: Sensor chain combiner (multiple sources → one enumerator)

### `repo/` — External data
- `github_releases.py`: GitHub releases API for update checks
- `http.py`: UrllibHttpFetcher — the only HTTP seam
- `data_install.py`: HttpDataInstaller — downloads + extracts .7z archives

### `theme/` — Cloud theme catalog
- `cloud.py`: CzhordeCatalog — cloud theme listing + download

### `infra/` — Infrastructure
- `logging.py`: `configure_logging()` — rotating file + stderr handlers.
  File handlers gated behind `TRCC_DEBUG=1` env var.
- `send_scheduler.py`: ThreadSendScheduler — thread-per-device send driver
- `sysinfo_config.py`: `SysInfoConfig` — manages `system_config.json` for
  sensor-dashboard panel layout. `auto_map()` returns bool indicating changes.

### `diagnostics/` — Health checks
- `adapter.py`: DiagnosticsAdapter — health/doctor/debug-report

---

## 6. UI Layer (`src/trcc/ui/`)

### GUI (`ui/gui/`) — Active/deployed UI
Absolute-positioning PySide6 UI. Key files:
- `__init__.py`: GUI composition root — QApplication setup, DPI scaling,
  bootstrap with splash, replay initial devices. Logging NOT configured here
  (caller's job).
- `trcc_app.py`: TRCCApp main window (~2888 lines). All signal wiring,
  event handlers, tray icon, device sidebar, panel switching.
- `lcd_handler.py`: LCDHandler — per-LCD-device GUI handler. Theme selection,
  video lifecycle, rendering, preview building, theme directory management.
- `led_handler.py`: LEDHandler — per-LED-device GUI handler.
- `base_handler.py`: BaseHandler interface for per-device handlers.
- `uc_system_info.py`: SystemInfoPanel — sensor dashboard. Loads
  `system_config.json`, calls `auto_map()`, saves only if changed.
- `uc_theme_setting.py`: Settings panel with overlay editor.
- `uc_theme_local.py`: Local theme browser.
- `uc_theme_web.py`: Cloud/web theme browser.
- `uc_theme_mask.py`: Mask browser.
- `uc_preview.py`: Device preview widget.
- `uc_device.py`: Device sidebar.
- `uc_about.py`: About panel with update check.
- `uc_activity_sidebar.py`: Sensor list sidebar.
- `uc_sensor_picker.py`: Sensor picker dialog.
- `uc_color_wheel.py`: Color wheel widget.
- `uc_info_module.py`: Info module widget.
- `uc_led_control.py`: LED control panel.
- `uc_screen_led.py`: Screen LED panel.
- `uc_image_cut.py`: Image crop tool.
- `uc_video_cut.py`: Video cut tool.
- `color_and_add_panels.py`: AddElementPanel, ColorPickerPanel.
- `overlay_element.py`: Overlay element editor.
- `overlay_grid.py`: Overlay grid widget.
- `screen_capture.py`: Full-screen capture overlay.
- `splash.py`: Startup splash screen.
- `bus_bridge.py`: EventBus → Qt signal bridge.
- `_ui_state.py`: UiStateStore — GUI-only prefs in `ui_state.json`.
  Save only called by mutator methods (user actions).
- `base.py`: BasePanel, helper functions.
- `constants.py`: All layout constants (Sizes, Layout, Colors, Styles).
- `assets.py`: Asset path mappings.

### qtgui (`ui/qtgui/`) — Newer refactored UI (not yet deployed)
Uses QLayout instead of absolute positioning. Panels in `panels/` subdirectory.

### CLI (`ui/cli/`)
Typer-based command-line interface. Key files:
- `main.py`: Entry point, configures logging, dispatches to subcommands.
  Calls `configure_logging()` with `platform.paths().log_file()`.
- `_ctx.py`: CLI context (App singleton management).
- `device.py`, `theme.py`, `config.py`, `display.py`, `led.py`, `system.py`:
  Subcommand groups.
- `shell.py`: Interactive shell with prompt_toolkit.

### API (`ui/api/`)
FastAPI REST API. Key files:
- `main.py`: FastAPI app factory. Token-based auth with pairing flow.
  `configure_auth(token)` sets persistent API token. `/health` and `/pair`
  exempt from auth.
- `devices.py`, `theme.py`, `display.py`, `led.py`, `config.py`, `system.py`:
  Route handlers that dispatch Commands.
- `schemas.py`: Pydantic models for request/response.
- `_shared.py`: Shared API utilities.

### Presentation (`ui/presentation/`)
Presentation models that map domain data to UI-friendly shapes:
- `device_presentation.py`, `lcd_panel.py`, `lcd_presentation_model.py`,
  `led_display.py`, `led_metrics_format.py`, `led_panel.py`, `led_zone_model.py`,
  `overlay_model.py`, `overlay_serialization.py`, `preview_geometry.py`,
  `sensor_display.py`, `slideshow_model.py`, `theme_directories.py`

### Other UI files
- `qapp.py`: QApplication-level config (silence Qt noise, disable High-DPI
  auto-scaling, global font, WMClass).
- `qt_tray.py`: System tray controller.
- `_errors.py`: UI error handling utilities.

---

## 7. App Hub (`src/trcc/app.py`, 836 lines)

`App` is the composition root that wires Platform + Devices + EventBus + Commands.

Key attributes:
- `platform`: the OS (Platform port)
- `devices: dict[str, Device]`: live devices keyed by `vid:pid`
- `events: EventBus`: synchronous event bus
- `settings: Settings`: user preferences
- `themes: ThemeService`, `media: MediaService`, `display: DisplayService`
- `metrics_loop: MetricsLoop`, `led_animation_loop: LedAnimationLoop`
- `led_effects: LEDEffectEngine`, `led_runtime: dict[str, LedRuntimeState]`
- `active_themes: dict[str, Theme]`: currently-loaded theme per device
- `senders: dict[str, DeviceSender]`: per-device send workers
- `data_install: DataInstallService`: per-resolution data installer
- `cloud_themes: CloudThemeService`: cloud theme catalog + service
- `diagnostics: Diagnostics`: health/doctor/debug
- `quickstart: QuickstartService`: guided first-session
- `first_run: FirstRunService`: first-run marker
- `_connect_issues: dict[str, ConnectResult]`: failed connections
- `last_raw_readings`: cached sensor sample for LED tick consumers

Key event subscriptions wired in `__init__`:
- `DeviceAttached` → `_on_device_attached`: hotplug auto-connect
- `OrientationChanged` → `_on_orientation_changed`: reload theme + mask from
  orientation-keyed resolution dir
- `SystemResumed` → `_on_system_resumed`: reconnect all devices after wake
- `OverlayChanged` → `_persist_user_mask_dc`: rewrite user mask's config1.dc

`dispatch(cmd)`: invokes `cmd.execute(self)`, logs entry/exit, catches exceptions,
publishes `ErrorOccurred` on failure.

---

## 8. Daemon & IPC

### `daemon.py` (191 lines)
Background process that owns USB + serves UIs. One process per user.
Opt-in via `TRCC_DAEMON=1` env var. No Qt event loop.
Lifecycle: check socket → build App → bind IPCServer → install signal handlers →
serve_forever.

### `ipc.py` (735 lines)
IPC over Unix-domain socket. Wire format: one line of JSON per request.
- Dispatch: `{"command": "SendColor", "kwargs": {...}}`
- Response: `{"type": "SendResult", "ok": true, ...}`
Reflective serialization over dataclasses.fields — adding a Command + Result is
zero-touch for IPC. Bytes encoded as `{"__bytes__": "<base64>"}`.

### `proxy.py` (58 lines)
AppProxy — client-side drop-in for App that talks to the daemon.
Only `dispatch(cmd) -> Result` is real. Other App attributes raise AttributeError.

### `_entry.py`
Shared CLI entry point. `python -m trcc` and `trcc` console script both
dispatch to `trcc.ui.cli.main.main()`.

---

## 9. Entry Points & Startup Flow

### `__main__.py`
Sets up early crash logging BEFORE any trcc imports. By default logging goes
to stderr only — no files written. Set `TRCC_DEBUG=1` to enable log file at
`~/.trcc/trcc.log` (or next to the exe for portable builds).

Startup sequence:
1. `__main__.py` — early logging shim (NullHandler or RotatingFileHandler)
2. `_entry.py` — dispatch to `ui.cli.main.main()`
3. `ui/cli/main.py` — Typer CLI root, configures logging via `configure_logging()`
4. Subcommand (`gui`, `serve`, `device`, `theme`, etc.) builds App via `_boot`
5. GUI: `ui/gui/__init__.py` — QApplication, DPI scaling, splash, bootstrap
6. CLI: direct Command dispatch
7. API: FastAPI app factory, uvicorn serve

### Console scripts (pyproject.toml)
- `trcc` → `trcc._entry:main`
- `trcc-gui` → `trcc.ui.cli.main:gui`
- `trcc-lcd` (gui-script) → `trcc.ui.cli.main:gui`

---

## 10. Settings & File Persistence

### Files TRCC writes

| File | When written | Controlled by |
|---|---|---|
| `trcc.json` | User changes a setting (language, brightness, theme, etc.) | Mutator methods only — never on startup |
| `ui_state.json` | User changes a GUI-only preference (last device, panel state) | Mutator methods only — never on startup |
| `system_config.json` | `auto_map()` changes sensor bindings | Conditional — only if `auto_map()` returns True |
| `trcc.log` | Only when `TRCC_DEBUG=1` env var is set | Environment variable |
| `trcc.latest.log` | Only when `TRCC_DEBUG=1` env var is set | Environment variable |
| `.first-run-done` | Once, on first run completion | `mark_completed()` — idempotent, not rewritten |
| Theme data archives | Device connects with a new resolution | Idempotent — only if not already present |
| User mask `config1.dc` | User edits overlay metric placement | `OverlayChanged` event handler |

### Config file locations
- Portable build: next to exe in `.trcc/`
- Installed: `~/.trcc/` (or `%APPDATA%\trcc` on Windows)
- Pre-cutover fallback: `trcc-next.json` (read-only, migrated on next save)

### Environment variables
- `TRCC_DEBUG=1`: Enable file logging (`trcc.log` + `trcc.latest.log`)
- `TRCC_DAEMON=1`: Run in daemon mode (IPC server, no Qt)

---

## 11. Device Protocol Details

### Handshake flow
1. `DiscoverDevices` scans USB bus for known VID:PID pairs
2. `ConnectDevice` opens the device, sends handshake command
3. Handshake response contains FBL byte + PM byte (+ optional SUB byte)
4. `get_profile(fbl, pm)` resolves to `DeviceProfile` (resolution, encoding,
   byte order, rotation flags)
5. Variant overrides applied post-handshake (button_image, panel_cutout)
6. `DeviceConnected` event published with resolved resolution
7. `ensure_all(resolution)` installs theme data if not present
8. Send worker started, `RestoreLastTheme` dispatched

### Frame encoding
- JPEG: FBL-dependent, quality varies by device
- RGB565: byte order (big/little endian) per DeviceProfile
- Rotation: non-square portrait panels pre-rotate 90° CW (simple panels) or
  use per-resolution encode table (widescreen panels)
- Widescreen panels (854x480, 1280x480, 1600x720, 1920x462): encode rotation
  is a fixed per-resolution base, NOT the whole-composite rotation

### Render pipeline (per tick)
1. DisplayService fetches background (image or current video frame)
2. Fit to device canvas (width/height/stretch mode)
3. Composite mask (if visible)
4. Render overlay elements (sensor text, clock, static text)
5. Blend bg_mask + overlay layers
6. Dim for brightness
7. Rotate to native buffer arrangement
8. Encode for wire (JPEG or RGB565)
9. Hand to DeviceSender → device.send()
10. `FrameSent` event published with surface for preview

### LED render pipeline (per tick)
1. LEDEffectEngine.tick() computes per-segment colors from mode + sensors
2. apply_brightness() scales colors by global brightness (single writer)
3. Construct LedPayload(colors, global_on)
4. device.send(payload) — wire-remap applied inside Led.send()
5. `LedColorsChanged` event published for preview

---

## 12. Build & Deploy

### PyInstaller build
```powershell
cd C:\trcc-src
python -m PyInstaller trcc-gui.spec --noconfirm --distpath dist
```

### Deploy to C:\trcc
```powershell
Stop-Process -Name trcc-gui -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\trcc\dist\trcc-gui" -ErrorAction SilentlyContinue
Copy-Item -Recurse "C:\trcc-src\dist\trcc-gui" "C:\trcc\dist\trcc-gui" -Force
New-Item -ItemType Directory -Force "C:\trcc\dist\trcc-gui\.trcc" | Out-Null
Set-Content -Path "C:\trcc\dist\trcc-gui\.trcc\winusb_consent.txt" -Value "granted" -Encoding ASCII
Start-Process -FilePath "C:\trcc\dist\trcc-gui\trcc-gui.exe" -Verb RunAs
```

### Required deploy files
- `.trcc\winusb_consent.txt` containing "granted" (USB access consent)

### Dependencies (pyproject.toml)
Core: PySide6, numpy, psutil, pyusb, libusb-package (Windows), click, typer,
fastapi, uvicorn, python-multipart, prompt_toolkit, sounddevice, wmi (Windows),
pythonnet (Windows), certifi, pyudev (Linux), nvidia-ml-py.
Optional: hidapi (hid extra), qrcode (remote extra), dbus-python + PyGObject
(wayland extra), pywin32 (windows extra).
Dev: pytest, pytest-cov, pytest-qt, ruff, httpx2.

---

## 13. Testing & Quality

### pytest
testpaths: `tests/`, pythonpath: `src`, `tests`. Verbose, short tracebacks,
`-n auto` (xdist parallel). Deprecation warnings from pyusb ignored.

### ruff
Line length 100, target py310. Selected rules: E, F, W, I, UP, B, SIM, PIE,
RUF, FA, PTH, TID251. UI layer enforces TID251 (no adapter imports past the
Trcc seam). Tests and dev scripts get relaxed rules.

### pyright
Python 3.10, basic type checking. Optional member access, attribute access,
argument type, call issue, optional iterable, optional operand = error.

### coverage
Branch coverage, multiprocessing+thread concurrency, parallel mode.

---

## 14. UI Automation & Verification

### Window detection
```python
hwnd = user32.FindWindowW(None, 'TRCC-Linux - Thermalright LCD Control Center')
```

### Screenshot capture
- Physical: 2908x1600 at 200% DPI
- Logical: 1454x800
- Use `ctypes.windll.user32.GetWindowRect` + `BitBlt` or PIL `ImageGrab`

### Layout diagnostic
- **F12 key** triggers `_run_layout_diagnostic()` in trcc_app.py
- Writes to `%TEMP%\trcc_layout_diagnostic.txt`
- Reports: window size, scaled constants, font sizes, overlaps, clipped text

### Windows API click automation
```python
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
# Convert logical to physical: x_phys = rect.left + int(x_logical * w / 1454)
# SendInput with MOUSEEVENTF_LEFTDOWN/UP
```

---

## 15. DPI Scaling

Qt 6 HighDPI scaling is always enabled. Manual DPI scaling + Qt dpr caused
double-scaling → window appeared at quarter size.

Solution: let Qt 6 handle ALL DPI scaling natively. Divide manual scale by
`devicePixelRatio` when dpr > 1.0. Base design size stays 1454x800 logical.

Key code in `src/trcc/ui/gui/__init__.py`:
```python
_dpr = _screen.devicePixelRatio()
if _dpr > 1.0:
    _scale = _scale / _dpr
    if _scale < 1.0:
        _scale = 1.0
```

---

## 16. Key UI Flows

### Settings → Sensor List Flow
1. Click **Settings tab** → `form_container` shows settings panels
2. Click **empty overlay grid cell** → `OverlayGridPanel.add_requested` signal
3. `UCThemeSetting._on_add_requested()` → shows `AddElementPanel` in `right_stack`
4. Click **"Hardware Data"** → `AddElementPanel.hardware_requested` signal
5. `TRCCApp._on_overlay_add_requested()` → `uc_activity_sidebar.setVisible(True)`
6. `UCActivitySidebar` shows scrollable sensor list grouped by category
7. Click a **sensor row** → `sensor_clicked` signal → adds to overlay, hides sidebar
8. Click **Close button** → `closed` signal → hides sidebar without adding

### Key layout positions (logical 1454x800)
- `FORM_CONTAINER = (180, 0, 1274, 800)` — Settings panel area
- `OVERLAY_GRID = (10, 1)` — Overlay grid within settings
- `RIGHT_STACK = (492, 1, 230, 430)` — Color/Add panel switcher
- `UCActivitySidebar` — `setGeometry(532, 128, 250, 500)` within form_container

### Category colors
- cpu=#32C5FF, gpu=#44D7B6, memory=#6DD401, hdd=#F7B501, network=#FA6401, fan=#E02020

---

## 17. Common Pitfalls

1. **Don't set QT_SCALE_FACTOR or QT_ENABLE_HIGHDPI_SCALING** — Qt 6 ignores them
2. **Don't call SetProcessDpiAwareness from Python** — PyInstaller bootloader sets it first
3. **PyInstaller runtime hooks can crash** with "Failed to import encodings module"
4. **Manual DPI scaling must be divided by dpr** to avoid double-scaling with Qt 6
5. **Window must be found by exact title** — `FindWindowW` is exact match only
6. **Click coordinates must be physical pixels** — convert from logical using dpr
7. **Deploy requires `.trcc\winusb_consent.txt`** — without it USB devices won't connect
8. **UI must not import `trcc.adapters.device`** — enforced by ruff TID251
9. **`configure_logging` runs exactly once per process** — GUI relies on CLI having called it
10. **Volatile wires (Bulk/LY) need keepalive** — firmware reverts to logo after ~2-3s
11. **`SensorsUpdated.readings` dict is shared** — subscribers must not mutate it
12. **`TRCC_DEBUG=1` required for log files** — normal use writes no log files

---

## 18. Backups
- `C:\trcc\dist\trcc-gui-backup3` — Before clipped text fixes
- `C:\trcc\dist\trcc-gui-backup4` — Before DPI scaling fix

# TRCC Project — Complete Knowledge Base

## Project Overview
TRCC (Thermalright LCD/LED Cooler Control) is a PySide6/Qt 6 desktop application
for controlling Thermalright LCD devices (e.g. 11.3" Trofeo Vision 9.16).

- **Source**: `C:\trcc-src\`
- **Deployed**: `C:\trcc\dist\trcc-gui\`
- **Build tool**: PyInstaller (`trcc-gui.spec`)
- **Python**: 3.14 (system), PySide6 (Qt 6)
- **Design size**: 1454x800 logical pixels
- **Target DPI**: 200% (dpr=2.0) → 2908x1600 physical

---

## Architecture

### UI Layer (two parallel implementations)
1. **`src/trcc/ui/gui/`** — Active/deployed UI (legacy, absolute positioning)
   - `trcc_app.py` — Main window (TRCCApp), 2888 lines, all signal wiring
   - `uc_activity_sidebar.py` — Sensor list sidebar (UCActivitySidebar)
   - `uc_theme_setting.py` — Settings panel with overlay editor
   - `uc_sensor_picker.py` — Sensor picker dialog (SensorPickerDialog)
   - `color_and_add_panels.py` — AddElementPanel, ColorPickerPanel
   - `uc_device.py` — Device sidebar
   - `uc_about.py` — About panel
   - `constants.py` — All layout constants (Sizes, Layout, Colors, Styles)
   - `base.py` — BasePanel, helper functions (create_image_button, etc.)
   - `assets.py` — Asset path mappings
   - `__init__.py` — DPI scaling computation (entry point)

2. **`src/trcc/ui/qtgui/`** — Newer refactored UI (not yet deployed)
   - Uses QLayout instead of absolute positioning
   - Panels in `panels/` subdirectory
   - `sensor_picker.py` — SensorPickerWidget (two-pane browser)

### Core Layer (`src/trcc/core/`)
- `models.py` — SENSORS dict, SENSOR_TO_OVERLAY, OverlayElementConfig, OverlayMode
- `commands.py` — All Command classes (ReadSensors, EnableOverlay, etc.)
- `registry.py` — USB device registry (VID:PID → metadata)
- `i18n.py` — Internationalization constants with position tuples

### Entry Points
- `src/trcc/ui/qapp.py` — `configure_qapplication()` sets global font
- `src/trcc/ui/gui/__init__.py` — DPI scale computation, creates TRCCApp
- `trcc-gui.spec` — PyInstaller spec
- `rt_hook_dpi.py` — Runtime hook (gutted to no-op)
- `qt.conf` — Qt platform config (dpiawareness=2)

---

## Key UI Flows

### Settings → Sensor List Flow
1. Click **Settings tab** (tab at top of form_container)
2. Click **empty overlay grid cell** → `OverlayGridPanel.add_requested` signal
3. `UCThemeSetting._on_add_requested()` → shows `AddElementPanel` in right_stack
4. Click **"Hardware Data"** → `AddElementPanel.hardware_requested` signal
5. `TRCCApp._on_overlay_add_requested()` → `uc_activity_sidebar.setVisible(True)`
6. `UCActivitySidebar` shows scrollable sensor list grouped by category
7. Click a **sensor row** → `sensor_clicked` signal → adds to overlay, hides sidebar
8. Click **Close button** (new) → `closed` signal → hides sidebar without adding

### Key Layout Positions (logical 1454x800)
- `FORM_CONTAINER = (180, 0, 1274, 800)` — Settings panel area
- `OVERLAY_GRID = (10, 1)` — Overlay grid within settings
- `RIGHT_STACK = (492, 1, 230, 430)` — Color/Add panel switcher
- `UCActivitySidebar` — `setGeometry(532, 128, 250, 500)` within form_container

---

## DPI Scaling Solution (Jul 22, 2026)

### Problem
Qt 6 HighDPI scaling is always enabled. Manual DPI scaling + Qt dpr caused
double-scaling → window appeared at 727x400 (quarter size).

### Solution
- Let Qt 6 handle ALL DPI scaling natively
- Divide manual scale by `devicePixelRatio` when dpr > 1.0
- Base design size stays 1454x800 logical; Qt scales to 2908x1600 physical
- Removed all QT_* env vars, SetProcessDpiAwareness, runtime hooks

### Key Code
`src/trcc/ui/gui/__init__.py` lines 148-168:
```python
_dpr = _screen.devicePixelRatio()
if _dpr > 1.0:
    _scale = _scale / _dpr
    if _scale < 1.0:
        _scale = 1.0
```

### Files Changed
- `src/trcc/ui/qapp.py` — Removed DPI env vars and SetProcessDpiAwareness
- `src/trcc/ui/gui/__init__.py` — Added dpr compensation
- `trcc-gui.spec` — Removed runtime_hooks
- `rt_hook_dpi.py` — Gutted to no-op

---

## Close Button on Sensor List (Jul 22, 2026)

### Problem
No way to close UCActivitySidebar without clicking a sensor.

### Solution
Added Close button at bottom of UCActivitySidebar.

### Files Changed
- `src/trcc/ui/gui/uc_activity_sidebar.py`:
  - Added `QPushButton` import
  - Added `closed = Signal()` to UCActivitySidebar
  - Close button: 28px height, #AAAAAA text on #2A2A2A bg, hover white on #3A3A3A
  - `_on_close()` emits `closed` signal
- `src/trcc/ui/gui/trcc_app.py` line 1827-1828:
  - `uc_activity_sidebar.closed.connect(lambda: self.uc_activity_sidebar.setVisible(False))`

---

## Build & Deploy Process

```powershell
# Build
cd C:\trcc-src
python -m PyInstaller trcc-gui.spec --noconfirm --distpath dist

# Deploy
Stop-Process -Name trcc-gui -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\trcc\dist\trcc-gui" -ErrorAction SilentlyContinue
Copy-Item -Recurse "C:\trcc-src\dist\trcc-gui" "C:\trcc\dist\trcc-gui" -Force
New-Item -ItemType Directory -Force "C:\trcc\dist\trcc-gui\.trcc" | Out-Null
Set-Content -Path "C:\trcc\dist\trcc-gui\.trcc\winusb_consent.txt" -Value "granted" -Encoding ASCII
Start-Process -FilePath "C:\trcc\dist\trcc-gui\trcc-gui.exe" -Verb RunAs
```

### Required Files in Deploy
- `.trcc\winusb_consent.txt` containing "granted" (USB access consent)

---

## UI Automation & Verification

### Window Detection
```python
hwnd = user32.FindWindowW(None, 'TRCC-Linux - Thermalright LCD Control Center')
```

### Screenshot Capture
- Use `ctypes.windll.user32.GetWindowRect` + `BitBlt` or PIL `ImageGrab`
- Physical size: 2908x1600 at 200% DPI
- Logical size: 1454x800

### Layout Diagnostic
- **F12 key** triggers `_run_layout_diagnostic()` in trcc_app.py
- Writes to `%TEMP%\trcc_layout_diagnostic.txt`
- Reports: window size, scaled constants, font sizes, overlaps, clipped text, widgets beyond parent bounds

### Windows API Click Automation
```python
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
# Convert logical to physical: x_phys = rect.left + int(x_logical * w / 1454)
# SendInput with MOUSEEVENTF_LEFTDOWN/UP
```

---

## Backups
- `C:\trcc\dist\trcc-gui-backup3` — Before clipped text fixes
- `C:\trcc\dist\trcc-gui-backup4` — Before DPI scaling fix

---

## Key Constants
- Window title: `TRCC-Linux - Thermalright LCD Control Center`
- Design size: 1454x800 logical
- Physical at 200% DPI: 2908x1600
- Font: Microsoft YaHei, base 10pt
- SENSORS dict in `core/models.py`: categories → (key_suffix, label, unit, metric_key)
- CATEGORY_COLORS: cpu=#32C5FF, gpu=#44D7B6, memory=#6DD401, hdd=#F7B501, network=#FA6401, fan=#E02020

---

## Common Pitfalls
1. **Don't set QT_SCALE_FACTOR or QT_ENABLE_HIGHDPI_SCALING** — Qt 6 ignores them
2. **Don't call SetProcessDpiAwareness from Python** — PyInstaller bootloader sets it first
3. **PyInstaller runtime hooks can crash** with "Failed to import encodings module"
4. **Manual DPI scaling must be divided by dpr** to avoid double-scaling with Qt 6
5. **Window must be found by exact title** — `FindWindowW` is exact match only
6. **Click coordinates must be physical pixels** — convert from logical using dpr
7. **Deploy requires `.trcc\winusb_consent.txt`** — without it USB devices won't connect

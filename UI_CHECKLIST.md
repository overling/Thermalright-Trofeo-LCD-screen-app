# TRCC UI Checklist — Everything the App Should Have and Display

> **Rule:** Every time you modify UI code, re-verify EVERY item on this list.
> If any item is broken, STOP and fix it before proceeding.

---

## 1. Main Window (`trcc_app.py`)

- [ ] Window title: "TRCC - Thermalright LCD Control Center"
- [ ] Window can be resized (not fixed size) — `setMinimumSize` used, not `setFixedSize`
- [ ] Window can be maximized via the maximize button
- [ ] Window can be restored to normal size
- [ ] Window can be closed via the close button
- [ ] Window can be minimized via the minimize button
- [ ] Window can be dragged by the title bar area
- [ ] `resizeEvent` fires on maximize/restore/manual resize
- [ ] `resizeEvent` proportionally repositions all child elements
- [ ] Central widget fills the entire window after resize

## 2. Sidebar — Device List (`uc_device.py`)

- [ ] Device buttons appear at the top of the sidebar
- [ ] Each connected device shows as a button
- [ ] Clicking a device button switches to that device
- [ ] "About" button is at the bottom of the sidebar
- [ ] Sidebar fills the full window height after resize
- [ ] Device scroll area fills the middle between buttons and About

## 3. Main Content Area — Panel Stack

- [ ] Mode buttons (tabs) are visible at the top: Local, Web, Mask, Image, Video, Settings
- [ ] Clicking a mode button switches the panel
- [ ] Panel switch triggers a resize event for the newly visible panel

### 3a. Local Themes Panel (`uc_theme_local.py` / `base.py`)

- [ ] Filter buttons visible: All, Default, User
- [ ] Slideshow toggle button visible
- [ ] Slideshow interval input visible
- [ ] Export button visible
- [ ] Theme thumbnails populate the scroll area grid
- [ ] Thumbnails are filtered by the active filter mode
- [ ] Clicking a theme thumbnail selects it and loads it to the device
- [ ] Delete buttons appear on user themes (index >= 5 or MODE_USER)
- [ ] Theme list includes BOTH shipped + user themes for the device's resolution
- [ ] **CustomBlack theme appears when the 480x480 device is active**
- [ ] Scroll area fills available width after window resize
- [ ] Filter buttons reposition after window resize

### 3b. Web Themes Panel (`uc_theme_web.py`)

- [ ] Web theme thumbnails populate
- [ ] Resolution label shows correct device resolution
- [ ] Clicking a web theme downloads and applies it

### 3c. Mask Panel (`uc_theme_mask.py`)

- [ ] Mask thumbnails populate
- [ ] Resolution label shows correct device resolution
- [ ] Clicking a mask selects it

### 3d. Image Cut Panel (`uc_image_cut.py`)

- [ ] Image cut canvas is visible
- [ ] Resolution matches device
- [ ] Panel resizes with window (uses `setMinimumSize`, not `setFixedSize`)

### 3e. Video Cut Panel (`uc_video_cut.py`)

- [ ] Video cut canvas is visible
- [ ] Resolution matches device
- [ ] Panel resizes with window (uses `setMinimumSize`, not `setFixedSize`)

### 3f. Settings Panel (`uc_theme_setting.py`)

- [ ] Settings panel is visible
- [ ] Panel resizes with window (uses `setMinimumSize`, not `setFixedSize`)

## 4. Preview Area (`uc_preview.py`)

- [ ] LCD preview image is visible on the right side
- [ ] Preview updates when theme changes
- [ ] Preview shows the correct resolution for the active device
- [ ] Preview repositions after window resize

## 5. Bottom Controls

- [ ] Rotation combo/dropdown is visible
- [ ] LDD button is visible
- [ ] Theme name input field is visible
- [ ] Save button is visible
- [ ] Export button is visible
- [ ] Import button is visible
- [ ] All bottom controls reposition after window resize

## 6. System Info View (`uc_system_info.py`)

- [ ] Sensor panels populate in a grid
- [ ] Page navigation (prev/next) buttons visible
- [ ] Page indicator label visible
- [ ] Clicking a sensor panel opens the sensor picker
- [ ] Sensor panels reposition after window resize
- [ ] Page nav buttons reposition after window resize
- [ ] Panel uses `setMinimumSize`, not `setFixedSize`

## 7. LED Control View (`uc_led_control.py`)

- [ ] LED control panel is visible
- [ ] Panel uses `setMinimumSize`, not `setFixedSize`

## 8. About View (`uc_about.py`)

- [ ] About panel is visible with app info
- [ ] Panel uses `setMinimumSize`, not `setFixedSize`

## 9. Activity Sidebar (`uc_activity_sidebar.py`)

- [ ] Activity sidebar visible when in theme editing mode (panel index 2)
- [ ] Activity sidebar hidden when not in theme editing mode

## 10. Theme Resolution Mapping

Themes are stored in per-resolution directories:
- `theme1920400/` → for 1920x400 devices (e.g. 0416:5408)
- `theme480480/`  → for 480x480 devices (e.g. 87ad:70db)
- `theme1920440/` → for 1920x440 devices

### Known themes by resolution:

**1920x400 (shipped):** Theme1, Theme2, Theme3, Theme4, Theme5
**1920x400 (user):** 11.3 inch, pink, Theme1, wide3, widescree

**480x480 (shipped):** Theme1, Theme2, Theme3, Theme4, Theme5
**480x480 (user):** CustomBlack, CustomBlk2, Theme1

**1920x440 (user):** Theme1, widescree

### Rules:
- [ ] Theme browser ONLY shows themes matching the active device's resolution
- [ ] User themes and shipped themes are both listed (deduped by path)
- [ ] `CustomBlack` shows when the 480x480 device (87ad:70db) is the active device
- [ ] `CustomBlack` does NOT show for the 1920x400 device (0416:5408) — different resolution

## 11. Window Controls (Title Bar)

- [ ] Minimize button visible in top-right
- [ ] Maximize/Restore button visible in top-right
- [ ] Close button visible in top-right
- [ ] All window control buttons reposition after window resize

## 12. DPI Scaling

- [ ] `Sizes` and `Layout` constants are scaled by the DPI factor
- [ ] Fonts are scaled by the DPI factor
- [ ] UI elements are readable at the current DPI setting

## 13. Build & Deploy

- [ ] App builds with PyInstaller without errors
- [ ] App deploys to `c:\trcc\trcc-gui.exe`
- [ ] App launches and runs without missing dependency errors
- [ ] App gets past the WinUSB driver consent (declined or granted)
- [ ] App connects to the active LCD device
- [ ] App renders frames to the LCD

---

## Pre-Change Verification Protocol

Before making ANY UI change:
1. Read this checklist
2. Note which items are currently working
3. Make the change
4. Re-verify EVERY item on this list
5. If any item broke, fix it immediately before moving on

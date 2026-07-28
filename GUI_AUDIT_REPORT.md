# TRCC GUI Best-Practices Audit (2026-07-15)

References consulted:
- Microsoft Windows 11 Design Principles (learn.microsoft.com/en-us/windows/apps/design/design-principles)
- Windows 11 Typography guidelines (learn.microsoft.com/en-us/windows/apps/design/signature-experiences/typography)
- Fluent 2 Type Ramp (fluent2.microsoft.design/typography)
- XAML type ramp values (learn.microsoft.com/en-us/windows/apps/develop/platform/xaml/xaml-theme-resources)
- WCAG 2.2 Contrast Minimum 1.4.3 (w3.org/WAI/WCAG22/Understanding/contrast-minimum)
- Qt 6 High DPI documentation (doc.qt.io/qt-6/highdpi.html)

## 1. Typography — FAIL

### 1a. Font family — non-compliant
- **Windows 11 standard**: Segoe UI Variable (primary), native system fonts for non-Latin
- **TRCC uses**: Microsoft YaHei (11 instances) + 1 Segoe UI
- **Issue**: Microsoft YaHei is a CJK font. While it covers Latin glyphs, it doesn't match the Windows 11 design language. Latin text in YaHei looks heavier and less polished than Segoe UI Variable.
- **Fix**: Use `QFont("Segoe UI Variable", 10)` as primary, fall back to Microsoft YaHei only when CJK glyphs are needed. Qt handles fallback automatically.

### 1b. Font sizes — below minimum
Windows 11 minimum: **12px Regular, 14px Semibold**. Text smaller than this is "illegible in some languages" per Microsoft.

TRCC font-size distribution (from 124 matches across source):
| Size | Count | Verdict |
|------|-------|---------|
| 6px  | 1     | WAY below minimum |
| 8px  | 5     | WAY below minimum |
| 9px  | 8     | WAY below minimum |
| 10px | 20    | Below minimum |
| 11px | 12    | Below minimum |
| 12px | 6     | At minimum (Regular only) |
| 13px | 4     | OK |
| 14px | 1     | OK (body) |
| 16px | 4     | OK |
| 18px | 2     | OK (body large) |
| 48px | 1     | OK (display) |

**46 of 124 text styles (37%) are below the Windows 11 minimum size.**

### 1c. Weight — uses Bold instead of Semibold
- **Windows 11 standard**: "Use Semibold instead of Bold. Bold is not part of the Windows type ramp."
- **TRCC uses**: `font-weight: bold` in multiple files (uc_sensor_picker.py, uc_theme_local.py, etc.)
- **Fix**: Replace `font-weight: bold` with `font-weight: 600` (Semibold) where the text is a title/heading.

### 1d. Type ramp — no hierarchy
Windows 11 defines a clear type ramp: Caption(12) → Body(14) → Body Strong(14) → Body Large(18) → Subtitle(20) → Title(28) → Title Large(40) → Display(68).

TRCC uses ad-hoc sizes (6, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 48px) with no clear semantic mapping. This makes the UI feel inconsistent.

## 2. Color Contrast — PARTIAL FAIL

WCAG 2.2 AA requires:
- 4.5:1 for body text (< 18pt)
- 3:1 for large text (≥ 18pt) and UI components

### Passing combinations (AAA / AA):
- White on black/dark: 13.77–21:1 ✅
- Light gray (220, D0D0D0, C0C0C0) on dark: 7.57–15.31:1 ✅
- Gold (180,150,83 / B4964F) on black: 7.42–7.43:1 ✅
- Green (00FF00) on dark: 10–15.3:1 ✅

### Failing combinations:
| Foreground | Background | Ratio | Verdict |
|-----------|-----------|-------|---------|
| #666 gray | #2D2D2D | 2.40:1 | **FAIL** |
| #666 gray | black | 3.66:1 | Large/UI only |
| #888 gray | #2D2D2D | 3.89:1 | Large/UI only |
| #AA0000 red | black | 2.71:1 | **FAIL** |
| #AA0000 red | #2D2D2D | 1.78:1 | **FAIL** |
| White on gold (180,150,83) | — | 2.83:1 | **FAIL** (if white text on gold bg) |
| Gold on #555 | — | 2.64:1 | **FAIL** |

**Key issues:**
1. `uc_system_info.py` uses `color: #666` and `color: #888` — these fail on dark backgrounds for body text
2. `uc_video_cut.py` uses `color: #AA0000` (red) for end-time label — fails contrast
3. If any white text is placed on the gold title bar, it fails (2.83:1). Title text should be **dark** on gold, not white.

## 3. DPI Handling — ACCEPTABLE (with caveats)

- **Per-Monitor DPI V2 awareness**: ✅ Set via `SetProcessDpiAwareness(2)` in `qapp.py:77`
- **QT_ENABLE_HIGHDPI_SCALING=0**: Deliberate choice — baked PNG backgrounds are 1× and would break under Qt auto-scaling. Manual scaling is done in `trcc.ui.gui.run()`.
- **Issue**: This means the app won't automatically adapt to high-DPI displays without manual code. On a 4K display at 200% scaling, the window may appear too small or require manual adjustment.
- **Recommendation**: This is a known tradeoff for PNG-background apps. Document it clearly. Consider migrating baked backgrounds to vector/SVG for proper DPI scaling in a future refactor.

## 4. Layout — MANUAL PIXEL POSITIONING

- TRCC uses `setGeometry(x, y, w, h)` with hardcoded pixel coordinates (see `constants.py` Layout class)
- **Windows 11 / Qt best practice**: Use layout managers (QVBoxLayout, QHBoxLayout, QGridLayout) for responsive, DPI-aware layouts
- **Issue**: Hardcoded coordinates break if window is resized, DPI changes, or font size changes
- **Recommendation**: Long-term, migrate to Qt layouts. Short-term, the manual scaling in `run()` handles the common case.

## 5. Alignment — OK

- Windows 11 default: Left alignment for text
- TRCC: Mostly left-aligned (acceptable)
- No issues found

## Summary Scorecard

| Category | Status | Severity |
|----------|--------|----------|
| Font family (YaHei vs Segoe UI Variable) | FAIL | Medium |
| Font sizes (37% below minimum) | FAIL | High |
| Font weight (Bold vs Semibold) | FAIL | Low |
| Type ramp hierarchy | FAIL | Medium |
| Color contrast (3 failing combos) | PARTIAL FAIL | High |
| DPI awareness | PASS (with caveats) | Low |
| Layout (manual positioning) | Non-standard | Low (long-term) |
| Alignment | PASS | — |

## Recommended Fixes (Priority Order)

1. **HIGH**: Fix failing contrast colors:
   - `uc_system_info.py`: Change `#666` → `#999` (4.6:1 on #2D2D2D), `#888` → `#AAA`
   - `uc_video_cut.py`: Change `#AA0000` → `#CC3333` (3.5:1 on black) or `#FF4444` (5.25:1)
   - Verify no white text on gold title bar (use dark text on gold)

2. **HIGH**: Increase below-minimum font sizes:
   - 6px, 8px, 9px → minimum 12px
   - 10px, 11px → minimum 12px (or 14px if semibold)
   - This affects 46 text styles across 8+ files

3. **MEDIUM**: Switch primary font to Segoe UI Variable with YaHei fallback:
   - `qapp.py:97`: `QFont("Segoe UI Variable", 10)` → fallback `QFont("Microsoft YaHei", 10)`

4. **MEDIUM**: Replace `font-weight: bold` with `font-weight: 600` (Semibold)

5. **LOW**: Long-term migration to Qt layouts and SVG backgrounds for proper DPI scaling

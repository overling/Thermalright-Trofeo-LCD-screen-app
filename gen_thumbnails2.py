"""Generate Theme.png thumbnails for all local themes by rendering bg + overlay."""
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

THEME_DIR = Path(r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400')
FONT_PATH = r'C:\trcc\dist\trcc-gui\_internal\trcc\assets\fonts\MSYH.TTC'
FONT_BOLD_PATH = r'C:\trcc\dist\trcc-gui\_internal\trcc\assets\fonts\MSYHBD.TTC'

SAMPLE_SENSORS = {
    'cpu:temp': 45.0,
    'cpu:usage': 35.0,
    'cpu:freq': 4200.0,
    'gpu:primary:temp': 55.0,
    'gpu:primary:usage': 60.0,
    'gpu:primary:clock': 1800.0,
    'gpu:primary:power': 120.0,
    'gpu:primary:vram_used_gb': 8.5,
    'gpu:primary:vram_total_gb': 16.0,
    'ram:usage': 45.0,
    'memory:used': 16.0,
    'memory:total': 32.0,
}

def get_font(size, bold=False):
    try:
        path = FONT_BOLD_PATH if bold else FONT_PATH
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def render_theme(theme_path):
    config_path = theme_path / 'trcc.json'
    if not config_path.exists():
        print(f"  SKIP: no trcc.json")
        return False
    
    with open(config_path, 'r', encoding='utf-8', errors='replace') as f:
        config = json.load(f)
    
    canvas = Image.new('RGBA', (1920, 400), (0, 0, 0, 255))
    
    # Try background: 00.png, then 01.png, then any *.png
    bg_name = config.get('background', '00.png')
    bg_path = theme_path / bg_name
    if not bg_path.exists():
        bg_path = theme_path / '00.png'
    if not bg_path.exists():
        bg_path = theme_path / '01.png'
    if bg_path.exists():
        try:
            bg = Image.open(str(bg_path)).convert('RGBA')
            if bg.size != (1920, 400):
                bg = bg.resize((1920, 400), Image.LANCZOS)
            canvas.paste(bg, (0, 0), bg)
        except Exception as e:
            print(f"  BG error: {e}")
    
    # Always draw overlay elements (for thumbnail preview)
    draw = ImageDraw.Draw(canvas)
    elements = config.get('elements', [])
    for el in elements:
        etype = el.get('type', '')
        x = int(el.get('x', 0))
        y = int(el.get('y', 0))
        color = el.get('color', '#ffffff')
        size = int(el.get('size', 24))
        bold = el.get('bold', False)
        
        try:
            rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        except Exception:
            rgb = (255, 255, 255)
        
        font = get_font(size, bold=bold)
        
        if etype == 'text':
            text = el.get('text', '')
            draw.text((x, y), text, fill=rgb, font=font)
        elif etype == 'metric':
            metric_id = el.get('metric', '')
            value = SAMPLE_SENSORS.get(metric_id)
            if value is not None:
                fmt = el.get('format', '{value}')
                try:
                    text = fmt.format(value=value)
                except Exception:
                    text = str(value)
                draw.text((x, y), text, fill=rgb, font=font)
        elif etype == 'clock':
            # Skip clock elements for thumbnail
            pass
    
    out_path = theme_path / 'Theme.png'
    canvas.convert('RGB').save(str(out_path), 'PNG')
    
    # Verify not black
    img = Image.open(str(out_path))
    ex = img.getextrema()
    is_black = all(e == (0, 0) for e in ex[:3])
    print(f"  SAVED: {out_path} black={is_black}")
    return True

print("Generating thumbnails for all local themes...")
for theme_path in sorted(THEME_DIR.iterdir()):
    if theme_path.is_dir():
        print(f"\n{theme_path.name}:")
        render_theme(theme_path)

print("\nDone!")

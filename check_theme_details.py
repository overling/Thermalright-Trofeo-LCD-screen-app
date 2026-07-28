import json, os
from PIL import Image

THEME_DIR = r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400'
for name in sorted(os.listdir(THEME_DIR)):
    path = os.path.join(THEME_DIR, name)
    if not os.path.isdir(path):
        continue
    cfg = os.path.join(path, 'trcc.json')
    bg = os.path.join(path, '00.png')
    if os.path.exists(cfg):
        with open(cfg, 'r', encoding='utf-8', errors='replace') as f:
            d = json.load(f)
        bg_name = d.get('background', '00.png')
        bg_path = os.path.join(path, bg_name)
        bg_exists = os.path.exists(bg_path)
        bg_black = True
        if bg_exists:
            img = Image.open(bg_path)
            ex = img.getextrema()
            bg_black = all(e == (0, 0) for e in ex[:3])
        els = len(d.get('elements', []))
        ov = d.get('overlay_enabled', False)
        print(f"{name}: bg={bg_name} exists={bg_exists} black={bg_black} overlay_enabled={ov} elements={els}")
    else:
        print(f"{name}: NO trcc.json")

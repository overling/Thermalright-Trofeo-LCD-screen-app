import json
from pathlib import Path

config_path = Path(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json')

with open(config_path, 'r') as f:
    d = json.load(f)

device_key = '0416:5408'
if device_key not in d['devices']:
    d['devices'][device_key] = {}

d['devices'][device_key]['current_theme'] = r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\Grey on Black'
# Clear user_overlay_elements so the theme's own elements are used
d['devices'][device_key]['user_overlay_elements'] = []

with open(config_path, 'w') as f:
    json.dump(d, f, indent=2)

# Verify
with open(config_path) as f:
    d = json.load(f)
dev = d['devices'][device_key]
print(f"current_theme: {dev.get('current_theme')}")
print(f"user_overlay_elements: {len(dev.get('user_overlay_elements', []))}")

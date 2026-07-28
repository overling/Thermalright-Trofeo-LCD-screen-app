import json

d = json.load(open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'))
dev = d['devices']['0416:5408']
print(f"overlay_enabled: {dev.get('overlay_enabled')}")
print(f"current_theme: {dev.get('current_theme')}")
print(f"user_overlay_elements: {len(dev.get('user_overlay_elements', []))}")

import json

path = r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'

with open(path, 'r') as f:
    d = json.load(f)

dev = d['devices']['0416:5408']
dev['overlay_enabled'] = True

with open(path, 'w') as f:
    json.dump(d, f, indent=2)

# Verify
with open(path) as f:
    v = json.load(f)
print(f"overlay_enabled: {v['devices']['0416:5408']['overlay_enabled']}")

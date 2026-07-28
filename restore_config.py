import json

# Read source config (has the correct user_overlay_elements)
with open(r'C:\trcc\.trcc\trcc.json') as f:
    source = json.load(f)

source_dev = source['devices']['0416:5408']
source_elements = source_dev.get('user_overlay_elements', [])
source_theme = source_dev.get('current_theme')

print(f"Source: {len(source_elements)} elements, current_theme={source_theme}")

# Read dist config
with open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json') as f:
    dist = json.load(f)

# Restore user_overlay_elements and current_theme from source
dist['devices']['0416:5408']['user_overlay_elements'] = source_elements
dist['devices']['0416:5408']['current_theme'] = source_theme

# Write back
with open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json', 'w') as f:
    json.dump(dist, f, indent=2)

# Verify
with open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json') as f:
    verify = json.load(f)

vdev = verify['devices']['0416:5408']
vels = vdev.get('user_overlay_elements', [])
print(f"\nVerified dist config:")
print(f"  user_overlay_elements: {len(vels)}")
for e in vels:
    print(f"    {e.get('id')} type={e.get('type')} metric={e.get('metric','')} size={e.get('size')}")
print(f"  current_theme: {vdev.get('current_theme')}")

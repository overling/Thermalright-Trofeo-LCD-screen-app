import json

# Check theme config
with open(r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\Grey on Black\trcc.json') as f:
    theme = json.load(f)
print('=== Theme elements ===')
for el in theme.get('elements', []):
    print(f"  id={el.get('id')} type={el.get('type')} metric={el.get('metric')} size={el.get('size')}")

# Check trcc.json user overlay elements
with open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json') as f:
    cfg = json.load(f)
dev = cfg['devices']['0416:5408']
print()
print('=== User overlay elements ===')
for el in dev.get('user_overlay_elements', []):
    print(f"  id={el.get('id')} type={el.get('type')} metric={el.get('metric')} size={el.get('size')}")

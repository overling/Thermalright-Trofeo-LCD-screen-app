import json

d = json.load(open(r'C:\trcc\.trcc\trcc.json'))
dev = d['devices']['0416:5408']
els = dev.get('user_overlay_elements', [])
print(f'Source config user_overlay_elements: {len(els)}')
for e in els:
    print(f"  {e.get('id')} type={e.get('type')} metric={e.get('metric','')} size={e.get('size')}")
print(f"current_theme: {dev.get('current_theme')}")

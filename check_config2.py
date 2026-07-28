import json
d = json.load(open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'))
dev = d['devices']['0416:5408']
els = dev.get('user_overlay_elements', [])
print(f'count={len(els)}')
for e in els:
    print(f'  {e["id"]} type={e["type"]} metric={e.get("metric","")} text={e.get("text","")} size={e.get("size")}')
print(f"current_theme: {dev.get('current_theme')}")

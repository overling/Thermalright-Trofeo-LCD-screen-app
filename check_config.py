import json
d = json.load(open(r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'))
els = d['devices']['0416:5408']['user_overlay_elements']
print(f'count={len(els)}')
for e in els:
    print(f'  {e["id"]} type={e["type"]} metric={e.get("metric","")} text={e.get("text","")}')

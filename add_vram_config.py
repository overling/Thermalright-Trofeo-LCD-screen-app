import json

path = r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'
d = json.load(open(path))

# Add VRAM elements to the existing user_overlay_elements for 0416:5408
els = d['devices']['0416:5408']['user_overlay_elements']

# Check if VRAM elements already exist
has_vram = any(e.get('metric', '').endswith('vram_used_gb') for e in els)
if not has_vram:
    # Find the max el_N id
    max_n = 0
    for e in els:
        eid = e.get('id', '')
        if eid.startswith('el_'):
            try:
                n = int(eid[3:])
                max_n = max(max_n, n)
            except ValueError:
                pass
    
    # Add VRAM elements matching the Grey on Black theme style
    new_els = [
        {
            "id": f"el_{max_n+1}",
            "type": "metric",
            "x": 1200,
            "y": 380,
            "color": "#A0A0A0",
            "size": 96,
            "bold": True,
            "italic": False,
            "text": "",
            "metric": "gpu:primary:vram_used_gb",
            "format": "{value:.0f}",
            "show_unit": False,
            "source": "time"
        },
        {
            "id": f"el_{max_n+2}",
            "type": "text",
            "x": 1320,
            "y": 380,
            "color": "#A0A0A0",
            "size": 96,
            "bold": True,
            "italic": False,
            "text": "-",
            "metric": "",
            "format": "{value}",
            "show_unit": True,
            "source": "time"
        },
        {
            "id": f"el_{max_n+3}",
            "type": "metric",
            "x": 1380,
            "y": 380,
            "color": "#A0A0A0",
            "size": 96,
            "bold": True,
            "italic": False,
            "text": "",
            "metric": "gpu:primary:vram_total_gb",
            "format": "{value:.0f}GB",
            "show_unit": False,
            "source": "time"
        },
        {
            "id": f"el_{max_n+4}",
            "type": "text",
            "x": 1276,
            "y": 480,
            "color": "#A0A0A0",
            "size": 64,
            "bold": True,
            "italic": False,
            "text": "VRAM",
            "metric": "",
            "format": "{value}",
            "show_unit": True,
            "source": "time"
        },
    ]
    els.extend(new_els)
    print(f"Added {len(new_els)} VRAM elements, total now {len(els)}")
else:
    print(f"VRAM elements already present, total {len(els)}")

json.dump(d, open(path, 'w'), indent=2)
print(f"Saved to {path}")

# Verify
d2 = json.load(open(path))
els2 = d2['devices']['0416:5408']['user_overlay_elements']
print(f"Verified: {len(els2)} elements")
for e in els2:
    print(f"  {e['id']} type={e['type']} metric={e.get('metric','')} text={e.get('text','')}")

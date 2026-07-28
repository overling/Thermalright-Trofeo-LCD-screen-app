import json

path = r'C:\trcc\dist\trcc-gui\.trcc\trcc.json'
d = json.load(open(path))

# Set the current_theme to Grey on Black
d['devices']['0416:5408']['current_theme'] = r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\Grey on Black'

# Set user_overlay_elements with all elements including VRAM
d['devices']['0416:5408']['user_overlay_elements'] = [
    {"id": "el_0", "type": "metric", "x": 196, "y": 96, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "", "metric": "cpu:temp", "format": "{value:.0f}C", "show_unit": True, "source": "time"},
    {"id": "el_1", "type": "metric", "x": 556, "y": 100, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "", "metric": "cpu:usage", "format": "{value:.0f}%", "show_unit": True, "source": "time"},
    {"id": "el_2", "type": "text", "x": 352, "y": 276, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "CPU", "metric": "", "format": "{value}", "show_unit": True, "source": "time"},
    {"id": "el_3", "type": "metric", "x": 1200, "y": 80, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "", "metric": "gpu:primary:temp", "format": "{value:.0f}C", "show_unit": True, "source": "time"},
    {"id": "el_4", "type": "metric", "x": 1580, "y": 88, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "", "metric": "gpu:primary:usage", "format": "{value:.0f}%", "show_unit": True, "source": "time"},
    {"id": "el_5", "type": "text", "x": 1276, "y": 283, "color": "#A0A0A0", "size": 48, "bold": True, "italic": False, "text": "GPU", "metric": "", "format": "{value}", "show_unit": True, "source": "time"},
    {"id": "el_6", "type": "metric", "x": 384, "y": 148, "color": "#6DD401", "size": 36, "bold": False, "italic": False, "text": "", "metric": "memory:temp", "format": "{value:.0f}C", "show_unit": True, "source": "time"},
    {"id": "el_7", "type": "metric", "x": 1200, "y": 380, "color": "#A0A0A0", "size": 56, "bold": True, "italic": False, "text": "", "metric": "gpu:primary:vram_used_gb", "format": "{value:.0f}", "show_unit": False, "source": "time"},
    {"id": "el_8", "type": "text", "x": 1320, "y": 380, "color": "#A0A0A0", "size": 56, "bold": True, "italic": False, "text": "-", "metric": "", "format": "{value}", "show_unit": True, "source": "time"},
    {"id": "el_9", "type": "metric", "x": 1380, "y": 380, "color": "#A0A0A0", "size": 56, "bold": True, "italic": False, "text": "", "metric": "gpu:primary:vram_total_gb", "format": "{value:.0f}GB", "show_unit": False, "source": "time"},
    {"id": "el_10", "type": "text", "x": 1276, "y": 440, "color": "#A0A0A0", "size": 42, "bold": True, "italic": False, "text": "VRAM", "metric": "", "format": "{value}", "show_unit": True, "source": "time"},
]

json.dump(d, open(path, 'w'), indent=2)
print(f"Saved {len(d['devices']['0416:5408']['user_overlay_elements'])} elements")

# Verify
d2 = json.load(open(path))
els = d2['devices']['0416:5408']['user_overlay_elements']
print(f"Verified: {len(els)} elements")
for e in els:
    print(f"  {e['id']} type={e['type']} metric={e.get('metric','')} text={e.get('text','')}")

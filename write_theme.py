import json
from pathlib import Path

theme_path = Path(r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\Grey on Black\trcc.json')

theme_config = {
    "name": "Grey on Black",
    "resolution": [1920, 400],
    "background": "01.png",
    "overlay_enabled": True,
    "mask_visible": True,
    "mask_position": [960, 200],
    "elements": [
        {"id": "cpu_temp", "type": "metric", "metric": "cpu:temp", "format": "{value:.0f}°C", "x": 20, "y": 20, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "cpu_usage", "type": "metric", "metric": "cpu:usage", "format": "{value:.0f}%", "x": 20, "y": 80, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "gpu_temp", "type": "metric", "metric": "gpu:primary:temp", "format": "{value:.0f}°C", "x": 20, "y": 140, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "gpu_usage", "type": "metric", "metric": "gpu:primary:usage", "format": "{value:.0f}%", "x": 20, "y": 200, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "gpu_clock", "type": "metric", "metric": "gpu:primary:clock", "format": "{value:.0f}MHz", "x": 20, "y": 260, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "gpu_power", "type": "metric", "metric": "gpu:primary:power", "format": "{value:.0f}W", "x": 20, "y": 320, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
        {"id": "vram_label", "type": "text", "text": "VRAM", "x": 500, "y": 320, "color": "#999999", "size": 42, "bold": False, "italic": False},
        {"id": "vram_used", "type": "metric", "metric": "gpu:primary:vram_used_gb", "format": "{value:.1f}", "x": 680, "y": 320, "color": "#cccccc", "size": 56, "bold": False, "italic": False, "show_unit": False},
        {"id": "vram_dash", "type": "text", "text": "-", "x": 780, "y": 320, "color": "#999999", "size": 56, "bold": False, "italic": False},
        {"id": "vram_total", "type": "metric", "metric": "gpu:primary:vram_total_gb", "format": "{value:.0f}GB", "x": 810, "y": 320, "color": "#cccccc", "size": 56, "bold": False, "italic": False, "show_unit": False},
        {"id": "ram_usage", "type": "metric", "metric": "ram:usage", "format": "{value:.0f}%", "x": 20, "y": 380, "color": "#cccccc", "size": 48, "bold": False, "italic": False, "show_unit": True},
    ]
}

with open(theme_path, 'w') as f:
    json.dump(theme_config, f, indent=2)

print(f"Written {len(theme_config['elements'])} elements to {theme_path}")

# Verify
with open(theme_path) as f:
    d = json.load(f)
for el in d['elements']:
    print(f"  id={el['id']} type={el['type']} metric={el.get('metric','')} size={el['size']}")

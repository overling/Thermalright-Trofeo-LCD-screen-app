import zipfile, json

for name in ['CustomBlack', 'CustomBlk2']:
    path = rf'C:\trcc\trcc-user\data\theme1920400\{name}.tr'
    z = zipfile.ZipFile(path)
    print(f"=== {name}.tr ===")
    print(f"Files: {z.namelist()}")
    if 'trcc.json' in z.namelist():
        j = json.loads(z.read('trcc.json'))
        for e in j.get('elements', []):
            print(f"  id={e.get('id')} type={e.get('type')} size={e.get('size')}")
    print()

# Compare with current trcc.json
for name in ['CustomBlack', 'CustomBlk2']:
    path = rf'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\{name}\trcc.json'
    with open(path) as f:
        j = json.load(f)
    print(f"=== {name} current trcc.json ===")
    for e in j.get('elements', []):
        print(f"  id={e.get('id')} type={e.get('type')} size={e.get('size')}")
    print()

import json

for theme_name in ['CustomBlack', 'Grey on Black']:
    path = rf'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400\{theme_name}\trcc.json'
    try:
        with open(path, 'r', encoding='latin-1') as f:
            d = json.load(f)
        print(f"=== {theme_name} ===")
        for e in d['elements']:
            print(f"  id={e.get('id','')} text={e.get('text','')} name={e.get('name','')} metric={e.get('metric','')}")
    except Exception as ex:
        print(f"=== {theme_name} === ERROR: {ex}")

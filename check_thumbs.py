from PIL import Image
import os

themes = ['CustomBlack','CustomBlk2','pink','Theme1','wide3','widescree','11.3 inch']
for n in themes:
    for base in [r'C:\trcc\trcc-user\data\theme1920400', r'C:\trcc\dist\trcc-gui\trcc-user\data\theme1920400']:
        p = os.path.join(base, n, 'Theme.png')
        if os.path.exists(p):
            img = Image.open(p)
            ex = img.getextrema()
            is_black = all(e == (0, 0) for e in ex[:3])
            print(f"{'BACKUP' if 'trcc-user' in base and 'dist' not in base else 'DIST  '} {n}: black={is_black} extrema={ex}")

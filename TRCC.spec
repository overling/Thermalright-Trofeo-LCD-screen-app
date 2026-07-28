# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules


hiddenimports = collect_submodules('usb')


a = Analysis(
    ['src\\trcc\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/trcc/assets', 'trcc/assets'),
        ('src/trcc/ui/gui/assets', 'trcc/ui/gui/assets'),
        ('src/trcc/assets/drivers', 'trcc/assets/drivers'),
        ('src/trcc/data', 'trcc/data'),
        ('lhm_nightly', 'lhm'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TRCC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TRCC',
)

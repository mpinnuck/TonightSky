# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TonightSky.py'],
    pathex=[],
    binaries=[],
    datas=[('celestial_catalog.csv', '.')],
    hiddenimports=[],
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
    name='TonightSky',
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
    icon=['TonightSky.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TonightSky',
)
app = BUNDLE(
    coll,
    name='TonightSky.app',
    icon='TonightSky.icns',
    bundle_identifier=None,
)

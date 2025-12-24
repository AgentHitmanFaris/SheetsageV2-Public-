# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['d:\\Document\\atoscore\\newUI\\launcher.py'],
    pathex=['d:\\Document\\atoscore\\atoscore_Core', 'd:\\Document\\atoscore\\newUI'],
    binaries=[],
    datas=[('d:\\Document\\atoscore\\newUI\\resources', 'resources'), ('d:\\Document\\atoscore\\atoscore_Core\\atoscore', 'atoscore'), ('d:\\Document\\atoscore\\atoscore_Core\\libs', 'libs')],
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
    name='atoscore',
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
    icon=['d:\\Document\\atoscore\\newUI\\resources\\logo.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='atoscore',
)


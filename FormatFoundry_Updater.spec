# -*- mode: python ; coding: utf-8 -*-
import sys

version_info = 'packaging/windows/FormatFoundry_Updater_version_info.txt' if sys.platform == 'win32' else None


a = Analysis(
    ['suite_updater.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/universal_file_utility_suite.ico', 'assets'),
        ('assets/universal_file_utility_suite_preview.png', 'assets'),
        ('update_manifest.example.json', '.'),
    ],
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
    a.binaries,
    a.datas,
    [],
    name='FormatFoundry_Updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/universal_file_utility_suite.ico'],
    version=version_info,
)

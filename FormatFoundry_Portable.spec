# -*- mode: python ; coding: utf-8 -*-
import sys

version_info = 'packaging/windows/FormatFoundry_version_info.txt' if sys.platform == 'win32' else None


a = Analysis(
    ['modular_file_utility_suite.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/universal_file_utility_suite.ico', 'assets'),
        ('assets/universal_file_utility_suite_preview.png', 'assets'),
        ('README.md', '.'),
        ('update_manifest.example.json', '.'),
        ('packaging/provenance/project-identity.json', 'provenance'),
    ],
    hiddenimports=['yaml', 'imageio_ffmpeg', 'torrentool.api', 'addons.idea_bank', 'addons.pc_health'] + (['windnd'] if sys.platform == 'win32' else []),
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
    name='FormatFoundry',
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
    icon=['assets/universal_file_utility_suite.ico'],
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FormatFoundry_Portable',
)

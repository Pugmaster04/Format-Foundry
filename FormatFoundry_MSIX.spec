# -*- mode: python ; coding: utf-8 -*-
import sys

common_data = [
    ('build/third-party-notices', 'third-party-notices'),
    ('assets/universal_file_utility_suite.ico', 'assets'),
    ('assets/universal_file_utility_suite_preview.png', 'assets'),
    ('assets/code_languages.json', 'assets'),
    ('README.md', '.'),
    ('LICENSE', '.'),
    ('THIRD_PARTY_NOTICES.txt', '.'),
    ('update_manifest.example.json', '.'),
    ('packaging/provenance/project-identity.json', 'provenance'),
]
app = Analysis(
    ['modular_file_utility_suite.py'], pathex=[], binaries=[], datas=common_data,
    hiddenimports=['yaml', 'imageio_ffmpeg', 'torrentool.api', 'pypdfium2', 'pypdfium2_raw',
                   'addons.idea_bank', 'addons.pc_health'] + (['windnd'] if sys.platform == 'win32' else []),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
updater = Analysis(
    ['suite_updater.py'], pathex=[], binaries=[], datas=common_data, hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0,
)
app_exe = EXE(
    PYZ(app.pure), app.scripts, [], exclude_binaries=True, name='FormatFoundry',
    debug=False, strip=False, upx=False, console=False,
    icon=['assets/universal_file_utility_suite.ico'],
    version='packaging/windows/FormatFoundry_version_info.txt',
)
updater_exe = EXE(
    PYZ(updater.pure), updater.scripts, [], exclude_binaries=True, name='FormatFoundry_Updater',
    debug=False, strip=False, upx=False, console=False,
    icon=['assets/universal_file_utility_suite.ico'],
    version='packaging/windows/FormatFoundry_Updater_version_info.txt',
)
coll = COLLECT(
    app_exe, updater_exe, app.binaries, app.datas, updater.binaries, updater.datas,
    strip=False, upx=False, name='FormatFoundry_MSIX',
)

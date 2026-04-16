# Universal Conversion Hub (UCH)

Universal Conversion Hub is a desktop toolkit for conversion, compression, extraction, media prep, archives, downloads, storage analysis, and batch utilities.

## Install

[![Windows installer](https://img.shields.io/badge/Windows-Download%20Installer-19786B?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Pugmaster04/Universal-File-Conversion/releases/latest/download/UniversalConversionHub_UCH_Setup.exe)
[![Ubuntu or Debian package](https://img.shields.io/badge/Ubuntu%20%2F%20Debian-Download%20.deb-19786B?style=for-the-badge&logo=ubuntu&logoColor=white)](https://github.com/Pugmaster04/Universal-File-Conversion/releases/latest/download/universal-conversion-hub-uch_latest_amd64.deb)

### Windows
1. Download the installer.
2. Run `UniversalConversionHub_UCH_Setup.exe`.
3. Launch `Universal Conversion Hub (UCH)` from Start or Desktop.

### Ubuntu 24.04 / Debian
1. Download the `.deb` package.
2. Install it:

```bash
sudo apt install ./universal-conversion-hub-uch_latest_amd64.deb
```

3. Launch it:

```bash
universal-conversion-hub-uch
```

If you prefer a manual artifact list instead of direct download buttons, use the [latest release page](https://github.com/Pugmaster04/Universal-File-Conversion/releases/latest).

## What It Includes

- Convert
- Compress
- Extract
- PDF / Documents
- Images, Audio, and Video workflows
- Archives
- Rename / Organize
- Duplicate Finder
- Storage Analyzer
- Checksums / Integrity
- Subtitles
- Aria2 downloads and torrents
- Presets / Batch Jobs

## Optional Backends

The app works without every backend, but broader format support improves when these are installed:

- FFmpeg + FFprobe
- Pandoc
- LibreOffice
- 7-Zip
- ImageMagick
- Aria2

Use the in-app `Backends / Links` tab to see what is detected and open the official install sources.

## Quick Start

1. Open a workspace tab.
2. Add files, folders, or download sources.
3. Review the module summary and workflow hints at the top of the tab.
4. Choose the output or action settings.
5. Run the job and review the status bar / activity log.

## For Users

- Full guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Archive policy: [archive/ARCHIVE_INDEX.md](archive/ARCHIVE_INDEX.md)

## For Developers

Run from source:

```powershell
python modular_file_utility_suite.py
```

Windows build:

```powershell
build_suite_release.bat
```

Linux build:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

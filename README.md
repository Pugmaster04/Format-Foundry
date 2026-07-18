# Format Foundry

Format Foundry is a cross-platform desktop toolkit for conversion, compression, extraction, media prep, downloads, archives, storage analysis, and repeatable batch workflows.

Canonical release: **Beta 0.5** (package version `0.5.0-beta`). Every earlier release is classified as Alpha.

Website:
- Overview: [index.html](https://pugmaster04.github.io/Format-Foundry/index.html)
- Downloads: [downloads.html](https://pugmaster04.github.io/Format-Foundry/downloads.html)
- License status: [license.html](https://pugmaster04.github.io/Format-Foundry/license.html)

## Install

[![Windows installer](https://img.shields.io/badge/Windows-Download%20Installer-19786B?style=for-the-badge&logo=windows&logoColor=white)](https://pugmaster04.github.io/Format-Foundry/downloads.html#windows-download)
[![Ubuntu or Debian package](https://img.shields.io/badge/Ubuntu%20%2F%20Debian-Download%20.deb-19786B?style=for-the-badge&logo=ubuntu&logoColor=white)](https://pugmaster04.github.io/Format-Foundry/downloads.html#linux-download)

The download page resolves the exact filenames from GitHub's current release assets and falls back to the release page instead of constructing a 404 URL. The [current release page](https://github.com/Pugmaster04/Format-Foundry/releases/latest) remains the complete artifact list.

Tagged releases include `SHA256SUMS`. After downloading it beside an installer, Linux users can verify matching files with:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

### Windows

1. Download `FormatFoundry_Setup_0.5.0-beta.exe`.
2. Run the installer.
3. Let the updater review optional feature tools, or clear that setup option to launch Format Foundry immediately.

The installer is self-contained. A normal Windows 10/11 computer does not need Codex, Python, the source repository, or any backend before installation. Setup scans the registered product identity and the standard install folder for older Format Foundry and legacy-name builds, then upgrades those files in place while preserving settings and output folders.

Uninstall:
- `File -> Uninstall...`
- `Settings -> Uninstall App`
- `Start -> Uninstall Format Foundry`
- Windows `Apps & Features`

### Ubuntu 24.04 / Debian

Use the packaged app. Normal Linux installs do not require the source folder after installation.

Recommended `.deb` install:

```bash
sudo apt install ./format-foundry_0.5.0-beta_amd64.deb
```

Launch:

```bash
format-foundry
```

Packaging note:
- A standalone `.deb` can expose full AppStream metadata such as links, release notes, screenshots, and license classification.
- GNOME Software trust badges like `Potentially Unsafe` and `No Software Repository Included` are tied to distribution channel trust, not just package metadata. To remove those, distribute through a signed APT repository or a sandboxed channel like Flatpak.

Portable AppImage fallback:

```bash
chmod +x FormatFoundry_linux_0.5.0-beta_x86_64.AppImage
./FormatFoundry_linux_0.5.0-beta_x86_64.AppImage
```

Uninstall:
- `File -> Uninstall...`
- `Settings -> Uninstall App`
- `sudo apt remove format-foundry`

## What It Covers

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

The app launches without any separately installed backend. Features tied to a missing tool remain unavailable or limited until that tool is installed:

- FFmpeg + FFprobe
- Pandoc
- LibreOffice
- 7-Zip
- ImageMagick
- Aria2

Use `Settings -> Backend Center` or launch `Format Foundry Updater --backends` to:

- Detect installed tools and versions in the background
- See exactly which workflows each missing tool affects
- Install through Windows Package Manager or the detected Linux package manager
- Open official project pages and documentation
- Copy a terminal-ready install command when direct installation is unavailable

Backend installers are intentionally not bundled into the normal app installer. Keeping them separate avoids stale third-party binaries, unexpected installer size, and mixed license/update responsibilities. A future offline backend pack should only be published with per-file licenses, checksums, provenance, and an independent update policy.

## Support And Security

- `Backends / Links` now shows detected backend versions, the current OS baseline, and the trusted update-host policy.
- `File -> Export Bug Report...` exports a JSON snapshot with OS details, backend versions, security settings, and recent log lines.
- Update checks can be restricted to trusted hosts in `Settings -> Security`.
- Update manifests can now declare compatibility metadata so the app/updater can avoid surfacing releases that are not targeted to the current OS or architecture.
- Beta and later tagged releases fail closed unless all Windows executables have valid, timestamped Authenticode signatures. The release also publishes `SHA256SUMS` and a Windows signature receipt.
- Beta 0.5 uses Git tag `v1.8.18` as a compatibility bridge for installed Alpha `1.8.17` updaters; the product label and every package filename remain `Beta 0.5` / `0.5.0-beta`.

## Need More Detail?

- Full guide: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
- Archive map: [archive/ARCHIVE_INDEX.md](archive/ARCHIVE_INDEX.md)

## From Source

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

`build_linux.sh` is for contributor/source builds. On Ubuntu/Debian it bootstraps a repo-local `.venv` automatically instead of expecting a pre-activated environment.
The script verifies its downloaded AppImage packaging tool before executing it.














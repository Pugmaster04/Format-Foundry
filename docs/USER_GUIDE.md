# Format Foundry User Guide

This guide keeps the detailed install, build, workflow, backend, and archive notes that used to live in the repo front-page README.

Version: **Beta 0.7.1** (`0.7.1-beta` package version)

Windows Beta packaging uses Microsoft Store MSIX; the Store listing is pending.
Use [Windows MSIX instructions](WINDOWS_MSIX.md) for the clean-clone build,
installed development-package test, Partner Center identity and submission steps.
The app's Store update/uninstall actions use Windows, while optional backend tools
continue through the included updater. Current Alpha EXE downloads remain in the archive.

Changelog:
- `CHANGELOG.md` (full project history and release notes)
- `archive/ARCHIVE_INDEX.md` (archive map and external archive-root policy)

Canonical release line:
- Beta 0.7.1 is the current unpublished Windows + Linux development milestone.
- Every public release through 1.8.17 is classified as Alpha, regardless of its historical numeric identifier. The earlier local Beta 0.5 milestone remains documented as Beta.

This is a modular desktop suite for practical file workflows:
- Convert
- Compress
- Extract
- Metadata
- PDF / Documents
- Images / Audio / Video
- Archives
- Rename / Organize
- Duplicate Finder
- Storage Analyzer
- Checksums / Integrity
- Subtitles
- Torrents
- Presets / Batch Jobs
- Development / Code Languages (offline reference and TypeScript-to-JavaScript generation)

### Code Language Library

Open **Workspace -> Development -> Code Languages** to browse rules, compare languages, inspect files and generate JavaScript from supported TypeScript files.

The bundled profiles cover Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, Swift, Kotlin, PHP, Ruby, R, Bash, PowerShell, SQL, Dart, Lua, HTML and CSS. HTML is labeled markup, CSS stylesheet, SQL query, and Bash/PowerShell shell; they are not all interchangeable programming languages.

1. Search by name, extension or topic, such as `.rs`, `ownership` or `nullable`.
2. Choose **Rules & Examples** for the selected language's baseline, typing, blocks, comments, variables, functions, control flow, collections, error handling, modules, runtime and porting pitfalls.
3. Choose a second language and **Compare Rules** to review semantic differences and a porting checklist. The comparison itself does not generate code.
4. Use **Inspect File...** for one UTF-8 source file up to 64 KiB. The app suggests languages from the extension, which is not proof of language. Shared extensions such as `.h` remain ambiguous. It does not scan a project or its dependencies.
5. Select **TypeScript** as source and **JavaScript** as target, then choose **Generate JavaScript...**. The app can reuse a selected `.ts`, `.mts` or `.cts` source, or ask you to select one. Choose an output filename; if it exists, the app picks a new numbered name. The source stays intact.
6. For a project with local imports, choose **Compile Project...**, select the folder containing `tsconfig.json`, then choose a `.zip` filename. The ZIP contains the generated JavaScript file tree and can be extracted into a separate folder. An existing ZIP is not overwritten. This action does not edit the source project.
7. **Compiler Setup** opens the official TypeScript instructions. Both compilation actions need Node.js and an installed TypeScript compiler (`npm install -g typescript`). Browsing the library needs neither tool, an AI service, an API key nor credits.
8. **Official Documentation** opens a browser through the app's external-link confirmation policy.

The single-file action uses the official compiler with strict checks, isolated module handling, a 25-second time limit and a 64 KiB UTF-8 input limit. It does not resolve imports or use a project configuration. `.ts` becomes `.js`, `.mts` becomes `.mjs`, and `.cts` becomes `.cjs`. Compiler errors do not create an output file. The app previews emitted JavaScript but does not run it or verify behavior against the source.

Project mode stages up to 256 regular UTF-8 files (512 KiB per file, 4 MiB total) from a folder no deeper than 16 levels. It uses TypeScript's resolved `tsconfig.json` to select files and honor ordinary compiler options, including local imports and include/exclude rules. It can take up to 60 seconds for each compiler pass. The combined generated text is limited to 8 MiB. The output is a staged, non-overwriting ZIP; source files and configured build folders are not modified. The generated code is not executed automatically.

Project mode skips `node_modules`, `.git`, `.venv`, `venv`, `build`, `dist`, `coverage`, and `.next`. It does not bundle external npm packages, run a bundler, or support TypeScript project references. It rejects configs that request `outFile`, declaration directories, incremental build metadata, or other settings that could write outside the staged output. Missing package dependencies or unsupported options produce an inline error and no ZIP. Runtime dependencies and behavioral equivalence still need your own review and tests after extraction.

Developers can install the pinned test compiler from the repo root with `npm ci --ignore-scripts --no-audit --no-fund`. This is a developer dependency, not a compiler bundled into consumer packages. Users of the installed app can install Node.js and TypeScript separately with the official instructions if they want this feature; the app explains when they are missing.

Inspection never executes code, imports a selected file, renders HTML, connects to a database, modifies originals, or uploads file contents. Reports omit source text, filenames and full paths; they are held in the interface rather than automatically saved. Python `.py`/`.pyw` files receive AST parsing using the Python version bundled with the app. Parse success is not proof of correct scope, types, imports, behavior or safety. Inspection of other languages is reference-only; the separate TypeScript-to-JavaScript action runs the TypeScript compiler. Legacy encodings and binary files are rejected rather than silently reinterpreted.

The library uses original, curated core summaries with named baselines, not downloaded specification text or a claim to support every latest feature. Official links may describe newer editions. SQL rules are deliberately a common subset; its documentation link is a PostgreSQL dialect reference, not a vendor-neutral SQL standard. Further cross-language pairs need separate, tested adapters or reviewed porting work, including library/API mapping and behavioral tests.

Contributors can extend `assets/code_languages.json` using schema version 1. Keep each profile's ten rule topics, baseline, original example, porting pitfalls and official HTTPS documentation link; bump the library revision when its content changes. Run `python -m unittest discover -s tests -p "test_language*.py" -v` after editing. The loader validates the bounded asset at runtime, and an unavailable/corrupt library disables only this section rather than the entire app.

Advanced media modules now include:
- Images: resize to fit, export to a chosen format, and optional sharpen pass
- Audio: format conversion, sample-rate conversion, mono/stereo control, loudness normalization, and silence trimming
- Video: remux, trim clips, stream-prep presets, and thumbnail-sheet generation

Image conversion coverage includes:
- Standard raster formats such as PNG, JPG, WEBP, BMP, GIF, TIFF, and ICO
- Modern Apple/HEIF-family formats such as HEIC, HEIF, and AVIF when the bundled `pillow-heif` plugin is available
- JPEG XL (`.jxl`) output plus common camera-raw inputs such as DNG, CR2/CR3, NEF, ARW, RAF, ORF, RW2, and PEF through the `ImageMagick` backend

### Adobe Interchange Files

Format Foundry converts supported interchange content, not editable Adobe projects. Adobe applications or a Creative Cloud subscription are not needed for the supported paths.

| Input | Supported workflow | Limits |
| --- | --- | --- |
| PDF | Convert / PDF Documents: all pages to TIFF, or page 1 to PNG/JPG at 150 DPI | No PDF-to-editable-Word conversion, OCR, form execution, or password entry |
| Illustrator AI saved with PDF compatibility | Same raster exports as PDF; also export the PDF document | Legacy PostScript AI is rejected; Illustrator editability is not retained |
| Photoshop PSD | Saved composite to standard raster formats; PDF through PDF / Documents | Basic 8-bit composites use Pillow; ImageMagick enables broader PSD variants |
| Photoshop PSB | Saved composite to standard raster formats or PDF | Requires ImageMagick; large files above the import limits are rejected |
| TIFF / TIF | Raster conversion; all pages to PDF in PDF / Documents | Images pipeline processes the first frame; layered TIFF is flattened |
| Camera RAW / DNG | Existing ImageMagick import to raster formats/PDF | Not Adobe Camera Raw's proprietary develop settings or Lightroom catalog support |

For all-page PDF-to-TIFF export, select **Convert** or **PDF / Documents**, add the PDF/AI, and choose `tiff`.
For multipage TIFF-to-PDF, use **PDF / Documents**, choose `pdf`, and add the TIFF.
The **Images** pipeline uses only the first PDF page / first TIFF frame; `keep` exports input-only PDF/AI/PSD/PSB as PNG.
PNG/JPEG exports are flattened pixels, not vectors. Layers, editable text objects, smart objects, spot colors and Adobe-specific color-management fidelity are not guaranteed.
PDF raster output and image-to-PDF paths use RGB pixels; do not use them as a lossless round trip for 16/32-bit channels or print-production color separations.
The native `.indd`, `.idml`, `.aep`, `.prproj`, `.fla`, `.xd`, and legacy `.eps`/`.ps` workflows are not supported. Export PDF, TIFF, PNG or standard media from the authoring app first.

PDF/AI rendering uses the bundled `pypdfium2` package. Source builds must install the updated `requirements.txt`; missing-renderer errors do not affect other modules.
This renderer does not initialize PDF forms or JavaScript actions. No ImageMagick PDF/PostScript security policy changes are needed.
Import limits are 128 MiB for PDF/AI/PSD/PSB, 100 pages for PDF/TIFF, 16 million rendered pixels per page, and 64 million pixels per all-page batch.
Conversions use staged files for PDF and image-to-PDF output, preserving an existing destination on failure or cancellation.
These limits are defensive resource bounds, not a sandbox or a guarantee that arbitrary untrusted documents are safe.

This file is the combined **README + How-To** guide.

## 0) Install/Launch Safety

Installer behavior is configured to reduce duplicate installs and preserve upgrades:
- Reuses previous install directory automatically (`UsePreviousAppDir`)
- Hides directory chooser for upgrades (`DisableDirPage=auto`)
- Detects running app/updater instances via mutex and requests closing before install (`AppMutex`)
- Replaces existing installed files with the new version during upgrade
- Scans the stable product registration and standard install folder for older Format Foundry or legacy-name builds
- Runs on a normal Windows computer without Codex, Python, a source checkout, or preinstalled backends

Runtime behavior:
- Main app is single-instance (one running copy at a time)
- Updater is also single-instance

Uninstall behavior:
- Windows installed builds now expose `File -> Uninstall...`, `Settings -> Uninstall App`, and a Start-menu shortcut named `Uninstall Format Foundry`
- Debian installs expose `File -> Uninstall...`, `Settings -> Uninstall App`, or the manual command:

```bash
sudo apt remove format-foundry
```

- AppImage copies are removed by deleting the `.AppImage` file
- Settings and output folders are not removed automatically

## 1) What The App Does

Format Foundry is designed as one desktop app with separate tools, instead of a single tangled converter view.

Core behavior:
- Queue-based processing for batch workflows
- Safe output conflict prompts (replace / rename / change location / cancel)
- Optional backend integrations for advanced formats
- Activity log for command/result visibility
- First-run setup, settings persistence, and update checks

## 2) UI Layout

Top tabs:
- Workspace
- Suite Plan
- Backends / Links
- Activity Log

Workspace now has a second navigation layer:
- Conversion
- Advanced
- Misc
- Aria2

Each of those category tabs contains the relevant module tabs for the current feature set.

The dedicated `Aria2` workspace category currently contains:
- `Downloads` for aria2-managed HTTP(S), FTP, SFTP, BitTorrent, magnet, and Metalink transfers
- `Torrents` for `.torrent` creation plus torrent download/extraction through `aria2c`

Linux note:
- If drag-and-drop is not available on a Linux build, the app now shows an explicit fallback message and the supported path remains `Add Files` / `Add Folder`.
- Linux CI now runs the built app and updater in headless `--smoke-test` mode after packaging, so the branch validates frozen runtime startup paths and settings-path resolution in addition to the raw build.

## 3) First Run + Settings

First launch opens setup wizard so you can configure:
- Output folder
- Theme and window mode
- Update checks
- Optional backend prompt behavior
- Update manifest URL

After that, use:
- `File -> Settings`

Settings page includes:
- Output path defaults
- Dark mode, fullscreen, borderless defaults
- Hover tooltip preference for advanced option explanations
  - Applies to Convert, Compress, Storage Analyzer, Duplicate Finder, and Backends / Links
- High contrast mode, interface scaling, and reduced-motion startup behavior for improved accessibility
- Startup animation toggle + duration
- FFmpeg thread count (`0` = auto)
- Activity log line retention
- Update and backend prompt settings
- Security controls:
  - confirm before opening external links
  - require HTTPS for backend/update links
  - require HTTPS for update manifest URLs
  - allow/block local manifest files
  - restrict update manifests/downloads to trusted hosts
- Support tools:
  - `Backends / Links` shows detected backend versions and the current environment support tier
  - `File -> Export Bug Report...` exports a JSON report with OS details, backend versions, settings, and recent logs

## 4) Quick Start

1. Open a module (example: Convert).
2. Add files or a folder.
3. Select valid options for the current queue type.
4. Confirm output path.
5. Run queue.
6. Review output and Activity Log.

Convert queue behavior:
- Queue is limited to one source extension at a time.
- Target format list updates to valid outputs for the current source type.
- Successful inputs leave the queue; failed or canceled inputs remain available for retry.
- Existing output names are preserved by choosing a numbered name. Enable `Settings -> Ask about existing output files` to choose replacement explicitly instead.
- Common processing tools keep their primary action and Stop button below the scrolling content.
- ZIP/TAR extraction uses a new destination rather than overwriting an existing extracted folder.

## 5) Optional Backends

The app opens without separately installed backends. Missing tools only disable or limit their related workflows:
- FFmpeg + FFprobe
- Pandoc
- LibreOffice
- 7-Zip (external app only; in-app extraction supports ZIP/TAR, not `.7z`)
- ImageMagick
- Aria2 (for torrent download / extraction)

Torrent note:
- Torrent file creation is built into the app through the bundled `torrentool` Python dependency.
- Torrent download and extraction requires the optional `Aria2` backend.
- The torrent workflow does not apply any download speed limit flags.

Updater backend center behavior:
- Open it from `Settings -> Backend Center`, the post-install option, or `FormatFoundry_Updater.exe --backends`
- Detects tools without blocking the interface
- Explains the feature impact of each missing tool
- Installs allowlisted packages through winget or the detected Linux package manager after explicit confirmation
- Provides official links and copyable commands when direct installation is unavailable

Backends panel behavior:
- Detected backend path: click to open file location
- Missing backend: click to open install link

## 5A) Optional Add-ons

### Idea Bank

Idea Bank is a built-in secondary workspace that is disabled by default. It is independent of file
conversion and does not require any optional backend.

Enable it from either location:

- `Settings -> Enable Idea Bank Add-on`
- `Settings -> Settings... -> Add-ons`

The workspace supports:

- Creating and editing ideas with notes
- Inbox, Exploring, Planned, Completed, and Archived statuses
- Comma-separated tags
- Search and status filtering
- CSV export

Idea data is written atomically to `addons/idea-bank/ideas.json` beneath the normal Format Foundry
settings directory. Disabling the add-on removes the top-level tab but keeps the data. Idea Bank does
not use the network and does not load third-party add-on code.

### PC Health Snapshot

PC Health Snapshot is a second built-in workspace that is disabled by default. Enable it from either
location:

- `Settings -> Enable PC Health Snapshot Add-on`
- `Settings -> Settings... -> Add-ons`

It provides a private, read-only summary of:

- Operating-system name, release, and architecture
- Available and total physical memory
- Free and total space on the home drive
- Microsoft Defender status on Windows

The add-on never changes files, security settings, or operating-system configuration. Its JSON export
does not include the computer name or user paths. Linux security providers differ by distribution, so
the Linux view directs users to their distribution security center rather than claiming a universal
provider result. This workspace is informational and is not antivirus software. Use `Open Storage
Analyzer` when deeper folder analysis is needed.

## 6) Update Sources

Use `Settings -> Update manifest URL` for app update checks.
You can also use the standalone updater executable (`FormatFoundry_Updater.exe`), which supports:
- Manifest URL
- Local manifest JSON file
- GitHub repo URL (checks latest release metadata/tags)

Default updater source:
- `https://github.com/Pugmaster04/Format-Foundry`

Updater security options include:
- HTTPS-only manifest/download URLs
- optional confirmation before opening download URLs
- SHA256 verification policy for downloaded update files
- optional trusted-host allowlist enforcement for manifests and download URLs

Official app and updater binaries expose their canonical, privacy-preserving project identity:

```text
FormatFoundry --provenance
FormatFoundry_Updater --provenance
```

Tagged release artifacts are also hash-bound to their source commit in `PROVENANCE.json` and
signed through GitHub artifact attestations. Verify a downloaded installer or package with:

```text
gh attestation verify <artifact-path> -R Pugmaster04/Format-Foundry
```

See [PROVENANCE.md](PROVENANCE.md) for the identity fingerprint, Authenticode check, and scope.

Example:

```json
{
  "latest_version": "v1.8.18",
  "release_label": "Beta 0.7.1",
  "package_version": "0.7.1-beta",
  "download_url": "https://github.com/Pugmaster04/Format-Foundry/releases/download/v1.8.18/FormatFoundry_Setup_0.7.1-beta.exe",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "notes": "Release notes here",
  "compatibility": {
    "platforms": ["windows", "linux"],
    "architectures": ["x86_64", "amd64"],
    "minimum_os_versions": {
      "windows": "10",
      "linux:ubuntu": "24.04"
    },
    "minimum_backends": {
      "ffmpeg": "6.0"
    }
  }
}
```

Manual check:
- `Help -> Check for Updates`

## 7) Build And Run

### Run from source

```powershell
python modular_file_utility_suite.py
```

### Build one-file EXE + installer

```powershell
build_suite_release.bat
```

Outputs:
- `dist\FormatFoundry.exe`
- `dist\FormatFoundry_Updater.exe`
- `installer_output\FormatFoundry_Setup.exe`
- `release_bins\FormatFoundry_<version>.exe`
- `release_bins\FormatFoundry_Updater_<version>.exe`
- `release_bins\FormatFoundry_Setup_<version>.exe`

`release_bins` is the staging folder for the current release line. Public release assets are versioned so the downloaded filenames match the shipped release exactly.

Official Beta Windows releases use Microsoft Store MSIX. Microsoft signs the package after certification; the MSIX build does not require a purchased certificate or signing subscription. See [WINDOWS_MSIX.md](WINDOWS_MSIX.md) for build, installed-test, migration and publication instructions.

See [WINDOWS_SIGNING.md](WINDOWS_SIGNING.md) only for a future independently signed EXE channel and the PFX explanation.

Branch CI validates an isolated development MSIX and, when the real Partner Center identity is configured, a Store submission package. Tagged publication requires installed MSIX validation, Store availability, license review and Ubuntu validation. Unsigned submission/test packages are CI artifacts; public Windows installation goes through Microsoft Store.

Beta 0.7.1 deliberately uses Git transport tag `v1.8.18`, which lets installed Alpha `1.8.17` updaters discover the lifecycle transition. Release titles, application UI, package metadata, and asset filenames continue to use `Beta 0.7.1` / `0.7.1-beta`.

### Linux build (preview)

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Linux outputs:
- `dist/FormatFoundry`
- `dist/FormatFoundry_Updater`
- `release_bins/FormatFoundry`
- `release_bins/FormatFoundry_Updater`
- `release_bins/FormatFoundry_linux_<version>_<arch>.tar.gz`
- `release_bins/format-foundry_<version>_<deb-arch>.deb`
- `release_bins/FormatFoundry_linux_<version>_<arch>.AppImage`

Linux release packaging:
- `build_linux.sh` now stages raw Linux binaries, creates a release tarball named `FormatFoundry_linux_<version>_<arch>.tar.gz`, builds a Debian package named `format-foundry_<version>_<deb-arch>.deb`, and builds an AppImage named `FormatFoundry_linux_<version>_<arch>.AppImage`
- Debian package installs to `/opt/format-foundry` and exposes launchers:
  - `format-foundry`
  - `format-foundry-updater`
- The AppImage contains the app, bundled updater binary, desktop metadata, and icon resources so it can launch without the source tree.
- Windows releases include `FormatFoundry_Portable_<version>_windows_x86_64.zip`, an optional one-folder build that starts without extracting a one-file bundle and does not require installation.
- The updater branch logic now prefers Linux `.deb` assets on Debian-family systems, then `.AppImage`, then `.tar.gz`

Ubuntu 24.04 install from `.deb`:

```bash
sudo apt install ./format-foundry_<version>_<deb-arch>.deb
```

Launch after `.deb` install:

```bash
format-foundry
```

The Debian package installs a standalone app under `/opt/format-foundry`. It does not rely on the source checkout after install.

Ubuntu 24.04 install from AppImage:

```bash
chmod +x FormatFoundry_linux_<version>_<arch>.AppImage
./FormatFoundry_linux_<version>_<arch>.AppImage
```

The AppImage is also self-contained. You can move it anywhere you want after download.

Optional AppImage launcher install:

```bash
mkdir -p ~/Applications
cp FormatFoundry_linux_<version>_<arch>.AppImage ~/Applications/
chmod +x ~/Applications/FormatFoundry_linux_<version>_<arch>.AppImage
~/Applications/FormatFoundry_linux_<version>_<arch>.AppImage
```

Ubuntu 24.04 build-from-source prerequisites:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk tk-dev dpkg-dev curl appstream
```

If `apt update` fails because of an unrelated third-party repository on your machine, fix or disable that repository first. That is outside this project's build logic.

Build from a clean clone:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

`build_linux.sh` now creates and reuses a repo-local `.venv` automatically. Do not run a system-wide `pip install` for this project on Ubuntu 24.04.

GitHub Actions Linux workflow:
- `.github/workflows/cross-platform-build-release.yml`
- Builds Linux artifacts on `ubuntu-latest`
- Uploads workflow artifacts for branch builds
- Validates the generated `.deb` layout in CI
- Smoke-tests the built AppImage in CI
- Uploads `FormatFoundry_linux_<version>_<arch>.tar.gz`, `format-foundry_<version>_<deb-arch>.deb`, and `FormatFoundry_linux_<version>_<arch>.AppImage` to tagged GitHub Releases
- Publishes `SHA256SUMS` so downloaded release artifacts can be verified independently

### Basic dependencies

For source development outside the Linux packaging flow:

```powershell
python -m pip install -r requirements.txt
```

## 8) Activity Log

The log tracks:
- Executed commands
- Workflow progress
- File output mapping
- Errors

Retention is configurable in Settings (`log_max_lines`) to avoid unbounded growth.

## 9) Performance Tips

- Use SSD output paths for faster batch writes.
- Install FFmpeg/FFprobe for media-heavy workflows.
- Tune FFmpeg threads in Settings:
  - `0` = backend default/auto
  - Higher values can increase speed and CPU usage
- Keep queues type-consistent.

## 10) Troubleshooting

Backend shows `Not found`:
- Install from Backends / Links tab
- Restart app
- Verify executable path exists

Wrong/limited conversion options:
- Queue may be extension-locked to a different source type
- Clear queue, add one known test file, then retry

No update results:
- Check manifest URL or GitHub repo URL
- Validate JSON keys and URL accessibility
- If using GitHub: publish a Release (recommended) or include `update_manifest.json` in the repo

## 11) Historical Snapshots / Backups

This repo uses automated historical snapshots:
- `tools/create_historical_snapshot.ps1`
- `.githooks/post-commit`

Default external snapshot location:
- `%USERPROFILE%\\Documents\\Universal File Utility Suite Output\\Format Foundry Archives\\history\\v<version>\\<timestamp>_<reason>\\`

Build script also runs snapshots:
- pre-build source snapshot
- post-build source + artifacts snapshot

Legacy imported archives are also stored in that external archive root, under:
- `legacy_universal_file_utility_suite`

Override location:
- Set environment variable `FORMAT_FOUNDRY_ARCHIVE_ROOT`

To enable local hooks in a clone:

```powershell
git config core.hooksPath .githooks
```

## 12) Important Paths

Windows settings file:
- `%LOCALAPPDATA%\FormatFoundry\settings.json`
- Legacy fallback: `%LOCALAPPDATA%\UniversalConversionHubHCB\settings.json`
- Legacy fallback: `%LOCALAPPDATA%\UniversalFileUtilitySuite\settings.json`
- Updater settings: `%LOCALAPPDATA%\FormatFoundry\updater_settings.json`
- Updater legacy fallback: `%LOCALAPPDATA%\UniversalConversionHubHCB\updater_settings.json`
- Updater legacy fallback: `%LOCALAPPDATA%\UniversalFileUtilitySuite\updater_settings.json`

Linux settings file:
- `$XDG_CONFIG_HOME/FormatFoundry/settings.json`
- Fallback: `~/.config/FormatFoundry/settings.json`
- Updater settings: `$XDG_CONFIG_HOME/FormatFoundry/updater_settings.json`
- Updater fallback: `~/.config/FormatFoundry/updater_settings.json`

Default output root:
- Windows: `%USERPROFILE%\Documents\Format Foundry Output`
- Linux: `~/Documents/Format Foundry Output`
- Linux fallback when `~/Documents` is absent: `~/Format Foundry Output`

Updater download folder default:
- Windows/Linux: `~/Downloads`
- Fallback when `~/Downloads` is absent: `~`

## 13) Legal/Safety Notes

- Use lawful personal workflows.
- Test on a small sample before large batch jobs.
- Keep backups for destructive operations.







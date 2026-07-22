# Format Foundry - Project Plan

## Vision
Build one desktop app with modular tools instead of a single tangled interface.  
Each module should be independently testable, replaceable, and extensible.

## Architecture
- One app shell (`Tkinter` notebook with tool tabs)
- Shared backend/task engine for processing
- Module-specific tabs for workflows and UI
- Preset and batch system for repeatable operations
- Cached, background external-backend detection (FFmpeg, FFprobe, Pandoc, LibreOffice, 7-Zip, ImageMagick, Aria2)
- Built-in optional add-ons that remain isolated from processing and are disabled by default
- Versioned settings migrations, atomic persistence, and a SQLite job ledger
- Shared accessibility, responsive-layout, task, security, and provenance foundations

## Phases

### Phase 1 (Implemented in starter)
- `Convert`
- `Compress`
- `Extract`
- `Metadata`
- `Presets / Batch Jobs`

### Phase 2 (Starter tab + base workflow)
- `PDF / Documents`
- `Archives`
- `Rename / Organize`
- `Checksums / Integrity`
- `Subtitles`

### Phase 3 (Starter tab + analysis tools)
- `Duplicate Finder`
- `Storage Analyzer`
- Dedicated advanced modules for:
  - `Images`
  - `Audio`
  - `Video`

## Current Deliverables
- App entrypoint: `modular_file_utility_suite.py`
- Updater entrypoint: `suite_updater.py`
- Release builds:
  - `FormatFoundry.exe`
  - `FormatFoundry_Updater.exe`
  - `FormatFoundry_Setup.exe`
  - `FormatFoundry_Portable_<version>_windows_x86_64.zip`
  - `format-foundry_<version>_amd64.deb`
  - `FormatFoundry_linux_<version>_x86_64.AppImage`
- Includes all requested module tabs:
  - Convert
  - Compress
  - Extract
  - Metadata
  - PDF / Documents
  - Images
  - Audio
  - Video
  - Archives
  - Rename / Organize
  - Duplicate Finder
  - Storage Analyzer
  - Checksums / Integrity
  - Subtitles
  - Presets / Batch Jobs
- Optional Idea Bank workspace
- Optional read-only PC Health Snapshot workspace

## Current Release Target
- Canonical coordinated release: `Beta 0.5` (`0.5.0-beta` package version)
- Migration transport tag: `v1.8.18` for installed Alpha `1.8.17` clients
- App version, updater version, installer metadata, manifest version, and public install docs must stay aligned through release-contract tests.

## Completed Beta Foundations
- Persistent SQLite job history and versioned settings migrations
- Capability-aware backend center with cached versions and direct/package-manager guidance
- Unit, contract, real-backend, responsive-layout, vulnerability, SBOM, and performance gates
- Windows installer, single-file executable, fast-start portable ZIP, Debian package, AppImage, and tarball
- Fail-closed tagged Windows signing, release checksums, provenance manifests, and GitHub attestations
- Two isolated built-in add-ons that are bundled but disabled by default

## Next Recommended Upgrades
Detailed execution order and release gates are maintained in `docs/POST_BETA_ROADMAP.md`.

1. Gradually split the main shell, shared widgets, stores, and module tabs into independently testable files.
2. Expand the shared cancellable-task abstraction across every long-running module.
3. Virtualize very large queue and directory-result views.
4. Add manual Narrator, Orca, keyboard-only, and real Ubuntu desktop install/launcher/uninstall checks to release sign-off.
5. Configure a publicly trusted Azure Artifact Signing or CA-issued certificate identity before publishing Beta binaries.
6. Keep third-party add-on loading disabled until signed manifests, compatibility rules, consent, and isolation are implemented.





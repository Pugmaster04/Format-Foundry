# Archive Index

This file is the archive index for the project.

Archive payloads now live outside the repo by default.

Default external archive root:
- `C:\Users\Pugma\Documents\Universal File Utility Suite Output\Format Foundry Archives`

## Canonical History Snapshots

These snapshots are generated from the canonical repo by the current release pipeline under:
- `Format Foundry Archives\history\v0.5`
- `Format Foundry Archives\history\v0.6`
- `Format Foundry Archives\history\v0.6.2`
- `Format Foundry Archives\history\v0.6.5`

Each snapshot folder contains:
- `source/`
- `artifacts/` for release-build snapshots
- `snapshot.json`

## Imported Legacy Lineage

These were imported from the earlier `Universal File Utility Suite` source tree in:
- `C:\Users\Pugma\Downloads\New Python Script Suite\archive`

Canonical imported location:
- `Format Foundry Archives\legacy_universal_file_utility_suite`

Imported versions:
- `v0.4.0`
- `v0.4.1`
- `v0.4.2`
- `v0.4.3`
- `v0.4.4`
- `v0.4.5`
- `v0.4.6`
- `v0.4.7`
- `v0.4.8`
- `v0.4.9`
- `v0.4.10`
- `legacy_root`

## Current Tools

Archive automation scripts:
- `tools/create_historical_snapshot.ps1`
- `tools/import_legacy_release_archives.ps1`

## Notes

- `v0.6.2` remains preserved under the external archive root in `history\v0.6.2` as the last `0.6.2` canonical line before the `0.6.5` optimization release.
- `v0.6.5` is the active optimized release line.
- Use the `FORMAT_FOUNDRY_ARCHIVE_ROOT` environment variable if you want the archive root somewhere other than the default sibling folder.

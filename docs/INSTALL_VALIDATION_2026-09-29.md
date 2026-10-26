# Beta 0.5 Install Validation

Date: 2026-09-29. Scope: locally rebuilt, unpublished Format Foundry 0.5.0-beta artifacts.

## Windows 11

- Backed up the previous `C:\Program Files\Format Foundry` installation and legacy local settings in `build/install-validation/pre-uninstall-20260929-145245.zip`, with file hashes in the adjacent JSON manifest.
- Built the app, updater, portable folder, and Inno Setup installer from the current source using the pinned requirements in an isolated Windows virtual environment.
- Ran the previous uninstaller elevated. Its log reports a complete removal and no restart requirement. Ran the new installer elevated and silently; its log reports success and no restart requirement.
- The installed app and updater hashes match the newly built binaries. The `HKLM` uninstall entry reports `0.5.0-beta`, and the installer created the Start Menu and uninstall shortcuts.
- The legacy `settings.json` SHA256 remained `98559AE7390DDA88BC492A34179B7DAF5444B0BB23CAA82185C184B174CE88B6` across uninstall and install.
- The installed app and updater passed `--version` and `--smoke-test` from a working directory outside the source tree. The installed GUI opened; its window was verified at `x=-1800, y=100, 1280x800` on the smaller monitor and closed cleanly. Its test configuration was isolated under `build/install-validation/gui-profile`.
- Frozen app, updater, and installer passed the size and startup performance budgets in `build/install-validation/frozen-windows-budget.json`.
- The pinned Windows environment passed 193 Python tests (9 skipped), CI-scope Ruff and mypy, and `pip check`.

## Ubuntu 24.04 WSL QA

- Built a fresh `.deb`, AppImage, and tarball from the same source. `tools/verify_linux_release.sh` passed checksums, Debian metadata and extraction, and app/updater smoke tests outside the source tree.
- Backed up the previously installed QA package files, package status, and `ffqa` configuration under `build/install-validation/linux-pre-uninstall-*`. The pre-build `.deb` is preserved under `build/install-validation/pre-rebuild-release_bins`.
- Removed the old package and verified its launcher and app binary disappeared. Installed the new `.deb` with `dpkg -i`; the installed launcher, desktop file, icon, metainfo, app, and updater passed checks.
- Removed it again, then installed the same local `.deb` with the documented `apt-get install ./package.deb` route. The installed package is `format-foundry` version `1:0.5.0~beta` and is left installed in the disposable QA distro.
- Installed app and updater smoke output is preserved in `build/install-validation/linux-apt-installed-*.json`. The pinned WSL environment passed 186 Python tests (11 skipped), CI-scope Ruff and mypy, and `pip check`.
- The website release contract test passed (1 test).

## Remaining Release Gates

- The locally built Windows installer and executable are **not Authenticode-signed**; no Windows signing credential is configured. Do not describe them as signed release assets.
- The old and new Debian packages share the same public version, so a package manager will not offer this local rebuild as a version upgrade. Assign a new version before publishing or testing an automatic update path.
- WSL verified package installation and headless startup, not a visible GUI launch on a physical Ubuntu desktop. A physical Ubuntu install/run check remains necessary before release.
- The Windows and Linux artifacts have not been published or validated as GitHub release downloads. The release CI has not run for this local source state.
- The WSL QA environment has no native Node.js/TypeScript compiler, so its real TypeScript compiler tests were skipped. Those tests ran in the Windows environment.

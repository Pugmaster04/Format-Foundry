# Clean Ubuntu WSL Installation Validation

Date: 2026-09-26, America/New_York (UTC-04:00).

## Scope And Safety

Tested the current local Beta 0.5 Linux artifacts in a newly imported Ubuntu
24.04.5 WSL2 instance named `FormatFoundry-QA-20260926`. The original `Ubuntu`
instance was not started or modified during this pass. The disposable instance
is retained, stopped, at `D:/Codex/Temp/FormatFoundry-QA-20260926` for follow-up.

The test instance was terminated at 23:13:55 Eastern, before the agreed 23:25
stop target and the user's 23:28 internet cutoff. All test GUI windows had been
closed, and no app, APT, or dpkg process was reported by the final process check.

This is real APT installation and WSLg GUI evidence, not merely extraction or
an Xvfb layout probe. It is **not** a native Ubuntu GNOME/Wayland desktop test,
and does not satisfy the existing native-Ubuntu release approval gate.

The checkout remains an uncommitted remediation worktree based on
`b0ccbe79148264995b6e2d20da2c929bb5944ad5`. Artifact hashes below identify exactly
what was tested; no new release, tag, publication, signing, or paid service was
created. No production source code or release binary was changed in this pass.

## Environment And Isolation

- Windows host: Windows 11, build 26200; WSL 2.6.3; WSLg 1.0.71.
- Guest: official Ubuntu 24.04.5 WSL amd64 image, Linux kernel
  `6.6.87.2-microsoft-standard-WSL2`.
- Root filesystem downloaded from [Canonical's Ubuntu 24.04 image directory](https://releases.ubuntu.com/noble/)
  and matched against its published SHA256SUMS.
- Created a non-root `ffqa` user. App and updater ran as this user from
  `/home/ffqa`, with installed resources under `/opt/format-foundry` and settings
  under `/home/ffqa/.config/FormatFoundry`.
- No source checkout, virtual environment, Codex installation, or project pip
  dependencies were installed in the guest. The host checkout remained mounted
  at `/mnt/d` for test drivers, fixtures, package input, and evidence output;
  therefore this does not claim the source directory was physically inaccessible.
- Baseline commands found none of the optional external backend executables.
  The app's bundled FFmpeg was detected without installing system FFmpeg.
- Initial APT installation and frozen CLI checks ran before adding GUI test
  tools. `python3-pil` and `libxtst6` were subsequently installed for native X11
  input/capture, not as application requirements. `x11-utils` was already present
  after the ordinary package dependency/recommendation installation.
- Aria2 was installed later for the backend-refresh test. The historical Alpha
  package later pulled in `python3-tk` through its own dependency declaration.
  These later changes must not be mistaken for the initial clean baseline.

## Results

| Check | Result and evidence |
| --- | --- |
| Clean consumer .deb installation | `apt install -y ./format-foundry_0.5.0-beta_amd64.deb` succeeded, with no preactivated venv or pip step. |
| Installed package health | `dpkg-query` reported `format-foundry 1:0.5.0~beta install ok installed`; `dpkg --audit` was empty. |
| App and updater CLI | Both installed launchers passed frozen smoke checks as `ffqa`; both report Beta 0.5. |
| Desktop resources | Verified the desktop entry, 256px icon, AppStream metadata, and installed package file list. |
| First-run UI | Captured the installed setup window and clicked Save and Continue; settings were saved and the main app appeared. |
| Startup animation | Observed the startup window during first-run completion. Changing animation frames were separately captured in the preceding desktop-validation pass. |
| Missing-backend guidance | A visible prompt listed missing tools and warned which workflows would remain limited. Clicking Yes opened the installed updater's Backend Center. |
| No graphical privilege helper | Clicking Install Selected for Aria2 displayed a clear warning that `pkexec` was unavailable and directed the user to the install command or official page. No silent failure or elevation bypass occurred. |
| Backend detection refresh | Installed Aria2 via administrator APT in the test guest, then clicked Refresh. The updater changed Aria2 to Detected, version 1.37.0, path `/usr/bin/aria2c`. This is not proof of graphical authorization/install success. |
| Uninstall | `apt remove -y format-foundry` removed both launchers, the installed main binary, and the desktop entry. Settings and a user-file fixture retained their SHA-256 values. |
| Genuine Alpha setup | Installed the public 1.8.17 .deb after removal, with a fresh profile; used its actual setup GUI to select dark mode and save preferences. |
| Alpha-to-Beta upgrade | Ordinary `apt install -y ./format-foundry_0.5.0-beta_amd64.deb` reported an upgrade from `1.8.17` to `1:0.5.0~beta`, without allowing a downgrade. Settings and fixture hashes were unchanged immediately afterward. |
| Installed desktop launch | Used `gio launch /usr/share/applications/io.github.pugmaster04.formatfoundry.desktop` as `ffqa`. The upgraded main window opened, retained dark mode, and did not repeat first-run setup. WSLg has no native GNOME app-menu surface to validate. |
| Settings migration | After GUI startup, all existing Alpha preference values remained identical. Only `compact_density=false`, `idea_bank_addon_enabled=false`, `pc_health_addon_enabled=false`, and `settings_schema_version=1` were added. |
| AppImage CLI | Normal `--version`, `--appimage-extract-and-run --version`, and extraction-fallback `--smoke-test` all exited 0. |
| Standalone AppImage GUI | Removed the .deb again and verified `/opt/format-foundry/FormatFoundry` was absent. Launched the AppImage normally from the user's home; its process ran from its own `/tmp/.mount_...` image. |
| AppImage conversion | Selected a generated PNG using the GUI file picker, clicked Convert Queue, and received a one-file completion message. Independently decoded the output as a 1600x1200 JPEG and preserved it as evidence. |
| Reinstall | Reinstalled Beta through APT after the AppImage test. Settings, the original user fixture, and the converted JPEG all retained their hashes. Final `dpkg --audit` was empty. |
| Shutdown | Closed test GUIs, checked app/package-manager processes, and terminated only the disposable distro. Both it and the untouched original Ubuntu instance were shown stopped. |

## Confirmed Defect Found

### P2: Updater Cannot Account For App-Bundled FFmpeg

On the same clean guest, the app reported one detected backend and successfully
resolved its bundled imageio FFmpeg. The updater's Backend Center instead showed
`0/7 tools detected` and labeled FFmpeg `Not installed`, with messaging that media
features were unavailable or limited. After Aria2 installation, the updater showed
1/7 while the app showed 2/7. These are not equivalent views of feature readiness.

Source pointers: `suite_updater.py:1706` calls `detect_backend_paths()` without
the app's fallback; `modular_file_utility_suite.py:1038` supplies the fallback;
`backend_support.py:252` handles it. A repair should distinguish app-bundled and
system-installed tools, without installing duplicate FFmpeg unnecessarily or
trusting a stale PyInstaller temporary path. Add packaged-app/updater regression
coverage. This defect is recorded, not fixed, in this time-bounded test pass.

The previously reported WSLg multi-monitor sizing issue was also reproduced:
the fresh main window initially used approximately 6195 pixels of width. The
existing small-screen Backends/Links layout and Windows OS-label findings remain
open; see [the desktop validation report](DESKTOP_VALIDATION_2026-09-26.md).

## Remaining Validation Limits

- Native clean Ubuntu desktop launcher/menu integration, App Center display,
  real graphical administrator acceptance/cancellation, and Wayland focus behavior.
- Clean Windows installer/UAC, uninstall, and installed Alpha-to-Beta migration.
- Full backend installation matrix, torrent transfers, long-running pause/stop,
  screen readers, all module layouts, and all conversion formats.
- AppImage GUI extraction fallback was not separately exercised; only its CLI
  fallback and normal GUI path were tested in this pass.
- No clean-clone rebuild, hosted CI, trusted signing, license/source attestation,
  or remote release change was performed. Existing release gates remain intact.

One test-driver process-ownership lookup hit an exited-process race after desktop
launch; its `OSError` handling was corrected in the local evidence driver. The
app was already running successfully. This was a harness error, not an app crash.

## Artifact Identity

| Artifact | SHA-256 |
| --- | --- |
| Official Ubuntu WSL rootfs | `bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e` |
| Beta .deb | `981472498472367b1ba4f069b13aef59a7100acc28888acab00c076767a3939f` |
| Public Alpha 1.8.17 .deb | `9e180cbaee36363d94fe7c0415ed417a004698a67a6def500974566a86ab7dc8` |
| Beta AppImage | `22900bf66b296c31f7cc115aa34b27dae798068d45c9daa39373b3594c68de95` |
| AppImage-converted JPEG | `72df8541e6b027b5b6f695986691c7137b82ce71961fadb4697b7486d2297176` |

The Alpha installer hash also matched the GitHub release asset's SHA-256 digest.

## Evidence And Follow-Up

Logs, screenshots, package inventories, settings snapshots/diffs, checksum checks,
test drivers, and converted-image evidence are under
`build/wsl-install-validation-2026-09-26/`.

A separate evidence archive and SHA-256 companion are preserved at:

`D:/Codex/Format Foundry Archives/audit-remediation-2026-09-26/wsl-install-validation-evidence.zip`

The archive excludes the large rootfs and installer downloads and does not contain
the WSL virtual disk. Those are retained locally, not deleted. No earlier backup
archive was overwritten. Resume the stopped test instance only for an explicitly
requested follow-up; there are no new scheduled or background test jobs.

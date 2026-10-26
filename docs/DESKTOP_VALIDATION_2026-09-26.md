# Desktop Interaction Validation

## Scope And Method

Tested the existing Beta 0.5 packages using operator-directed native window
interaction, screenshots, file pickers, and actual output-file inspection.
This is more than headless CLI smoke testing, but is not a human sitting at a
freshly installed consumer desktop. It does not close the clean-install gate.

- Windows: actual packaged one-file app and updater on Windows 11 Home,
  version 10.0.26200. Separate test HOME/USERPROFILE/APPDATA/LOCALAPPDATA.
- Linux: actual app and updater extracted from the .deb into
  `/tmp/foundry-desktop-check-qijwpyi_`, running under Ubuntu 24.04.4 WSLg/X11.
  Separate HOME, XDG config/cache/runtime paths; working directory outside the
  checkout. No `apt install`, native desktop launcher, or package uninstall test.
- No optional backends were installed or removed; both development environments
  already had detected backends. This is not missing-backend consumer proof.
- No security settings, installed application, release policy, public release,
  or production source files were changed during this validation.
- Test drivers use OS window/input APIs, not direct app callbacks. Some early
  driver attempts were rejected by ownership guards or needed input-adapter
  corrections; those attempts are not recorded as application defects.

## Findings

### P2: Backends / Links Does Not Fit At High Scaling

Confirmed in the packaged Windows app at a 1024x768 outer window and 160%
interface scaling. The single-row toolbar clips its right-hand actions, and
the link/detail fields become too narrow to read. The app is responsive and
the paned layout remains present, but its default allocation is not usable.

Evidence: `windows-main-dark-160.png`.

Code: `modular_file_utility_suite.py`, `BackendLinksTab`, toolbar around line
7168 and horizontal pane/table sizing around line 7212. Use a wrapping toolbar
and responsive pane orientation/initial sizing; add this tab at 160% to the
layout test matrix. The previous layout probes did not cover this surface.

### P2: Windows 11 Is Reported As Windows 10

Confirmed in the packaged updater. Windows CIM reports Windows 11 Home, build
26200, while the updater displays Windows 10. The local Python 3.11.9 runtime
also reports release `10`; `collect_os_details()` currently forwards
`platform.uname().release` without Windows product-version normalization.

Evidence: `test-environment.json` and `windows-updater-check.png`.

Code: `support_runtime.py:334`. Correct the Windows client OS naming/version
normalization while preserving the raw kernel/build version. Add Windows 10,
Windows 11, and Windows Server regression cases. The wrong display is proven;
a resulting incorrect compatibility decision was not exercised in this pass.

### P2: WSLg Multi-Monitor Startup Uses The Combined Desktop Width

Confirmed only under WSLg: X11 advertises a 7040x1440 combined desktop, and
the app initially opens at approximately 6195 pixels wide. This recurred on
reopening. Resizing the window to 1024x768 worked normally.

Evidence: `linux-environment-final.txt`; live `xwininfo` recorded 6195x1296 on initial
startup and 6195x1336 on reopening. The captured `linux-main.png` and
`linux-reopened.png` show the manually resized state, not the initial width.

Code: `modular_file_utility_suite.py:5901`, `_calculate_display_matched_geometry()`
uses 88% of `winfo_screenwidth()` on Linux. Prefer the current monitor's work
area, with a conservative fallback cap. Native Ubuntu multi-monitor behavior
still needs confirmation; do not generalize this as a proven GNOME defect.

## Completed Checks

| Check | Result / Evidence |
| --- | --- |
| Windows first-run setup | Opened without an existing profile; Save and Continue remained visible after resizing to 660x480 outer dimensions. |
| Windows first-run scrolling | Wheel input exposed the lower content without hiding the fixed action row. |
| Windows setup acceptance | Clicked Save and Continue; `first_run_done` persisted and the main window opened. |
| Windows image conversion | Added a generated 1600x1200 PNG through the native file picker; clicked Convert Queue; decoded and inspected the resulting JPEG. |
| Windows output collision | Repeated conversion created `sample (1).jpg`; the SHA-256 of the original `sample.jpg` remained unchanged. |
| Windows failed queue preservation | Submitted a valid image plus a deliberately invalid PNG. The valid item succeeded and left the queue; the invalid item remained with a visible error. |
| Windows settings | Opened through the Settings menu; Save/Cancel remained visible at 800x600. Saved dark mode and 160% scaling to the isolated profile. |
| Windows close/reopen | Closed the app and reopened the packaged executable without a stale-instance error or repeated setup wizard. |
| Windows duplicate launch | A second simultaneous invocation displayed the expected already-running warning. |
| Windows updater | Clicked Check for Updates; retrieved Alpha 1.8.17 Windows installer URL and SHA-256; correctly reported Beta 0.5 as already up to date. No installer was downloaded or run. |
| Linux first-run setup | Opened from extracted .deb; Save and Continue remained visible at 640x440 and successfully saved the isolated settings. |
| Linux startup animation | Captured ten changing frames; inspected frames showing 19% and 78% progress and different logo positions. Main window appeared afterward. |
| Linux image conversion | Used the Linux file picker and Convert Queue; resulting JPEG decoded at 1600x1200 with expected image content. |
| Linux close/reopen | Used the window close protocol, relaunched the extracted app, and reached the main window without first-run or stale-lock problems. |
| Linux updater | Clicked Check for Updates; selected the public amd64 .deb, retrieved SHA-256, identified Ubuntu 24.04.4, and did not treat Alpha as newer than Beta. |
| Linux updater scrolling | Wheel input exposed release metadata while the fixed action row remained reachable. |
| Supplementary Windows source UI probes | All 17 automated cases passed, separately from the packaged-window interactions above. |

## Not Yet Tested

Follow-up: [clean WSL installation validation](WSL_INSTALL_VALIDATION_2026-09-26.md)
now covers APT installation, uninstall/reinstall, Alpha-to-Beta migration, missing
backend guidance, and standalone AppImage GUI conversion. The list below records
the limits of this earlier desktop pass; native Ubuntu desktop approval is still
outstanding.

- Fresh Windows installer installation, elevation acceptance/cancellation,
  installed updater handoff, uninstall, or Alpha-to-Beta installed migration.
- A clean Ubuntu desktop installation through APT, application-menu launching,
  installed-package upgrading/uninstallation, or a native GNOME Wayland session.
- AppImage GUI and Windows portable ZIP GUI during this pass.
- Missing-backend prompts/installation on a genuinely backend-free machine.
- Manual long-running cancellation/pause, real torrent selection, all conversion
  formats, screen readers, full keyboard traversal, or startup focus-loss restore.
- Hosted CI and trusted signatures. No release gate was marked satisfied.

## Evidence And Preservation

Evidence is under `build/desktop-validation-2026-09-26/`. It includes process-scoped
test drivers, screenshots, generated fixtures/output, an environment/hash record,
isolated settings, and the separate Windows layout-probe report. Large incidental
Windows shell caches in the isolated profile are not needed as evidence.

The tested artifact SHA-256 values are:

| Artifact | SHA-256 |
| --- | --- |
| Windows app | `42B53838BB69CB9EB8CC03EA183EE47E053C0DDCC478E35F5BF7FD502D96F40F` |
| Windows updater | `8601A736510CFE1078A2D0A702FF99343A3D5F3DDE3789595FA8260EBB3E3781` |
| Linux .deb | `981472498472367B1BA4F069B13AEF59A7100ACC28888ACAB00C076767A3939F` |

Test application/updater sessions were closed after validation. Test evidence
remains available; no source fixes or new release builds were made in this pass.
The Linux temporary profile was no longer present after the WSL session ended;
its first-run persistence was observed live, but a final copy of that profile
could not be retained. Screenshots and the converted Linux image were preserved.

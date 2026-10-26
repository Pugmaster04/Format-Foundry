# Time-Bounded Linux Fixes

Follow-up to WSL_INSTALL_VALIDATION_2026-09-26.md, before the 23:25 Eastern stop
target on September 26. These are source fixes, not rebuilt release artifacts.

## Changes

- Updater asks its adjacent, matching-version packaged app for FFmpeg readiness
  when no external FFmpeg is detected. It reports "Included in app", excludes it
  from missing-tool installation, and never retains an expired one-file extraction
  path as an executable. Missing, mismatched, or failed app probes fail safely.
- Linux startup and centering use the monitor containing the pointer via bounded
  XRandR discovery. Missing XRandR falls back to conservative window bounds rather
  than sizing a window against the entire combined multi-monitor desktop.
- Backends/Links actions wrap into rows. Backend list and link fields use a
  vertically resizable split instead of competing for horizontal space. Added a
  horizontal tree scrollbar and wrapping support actions; link entries retain
  their full usable width. Existing module scrolling remains available.

## Verification

- Four new regression tests pass on Windows and Linux.
- Sixteen existing audit regression tests pass on Windows and Linux.
- Python compilation and `git diff --check` pass.
- Real WSLg source UI at 1024x768 and 160% scale: six backend actions fit
  horizontally, and six link fields measured 634 pixels wide.
- Measured startup geometry changed from roughly 6195 pixels wide to
  `2252x1290+2074+75`, inside the selected 2560-pixel monitor.
- The changed updater helper queried the actual installed Beta binary and
  correctly reported bundled FFmpeg 7.0.2-static without exposing its temp path.
- Evidence, screenshots, and test harness are in `build/linux-fixes-2026-09-26/`.

The final expanded scroll-reachability probe incorrectly included the fixed
footer button outside the canvas. Its widget filter was corrected, but the
corrected expanded probe was not rerun before the deadline. The earlier
horizontal-fit, field-width, geometry, and live FFmpeg checks passed; full
scroll-reachability coverage remains unverified. The test distro was stopped
at 23:24:27 Eastern. No package rebuild was started.

The initial pytest command was unavailable in the Windows environment; tests
were run successfully with their native unittest runner instead. No dependency
installation was needed for this fix pass.

## Outstanding

The existing .deb, AppImage, and Windows executables still contain the previously
built code. Rebuild and repeat packaged GUI checks before distributing these
fixes. Native Ubuntu desktop validation, graphical package-manager authorization,
the Windows OS-label issue, signing/licensing review, and hosted CI remain open.
No release gate was bypassed and no release was published.

Affected source before edits is preserved in
`D:/Codex/Format Foundry Archives/audit-remediation-2026-09-26/linux-fixes-before-2319.zip`.

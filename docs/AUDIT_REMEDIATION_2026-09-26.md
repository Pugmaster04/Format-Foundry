# September 2026 Audit Remediation

Scope: all 35 findings in the September 26 audit, ordered by risk. Changes are on
`codex/audit-remediation`, based on `b0ccbe79148264995b6e2d20da2c929bb5944ad5`.
Product identity remains the unpublished Beta 0.5. No release was published and no
signing credentials, user settings, or installed system packages were changed.

## Itemized Disposition

| # | Finding | Remediation / Remaining Boundary |
| --- | --- | --- |
| 1 | Rename collision data loss | Reserve complete preview targets; exclusive links, revalidation, rollback. Existing files are never silently replaced. Unsupported hard-link filesystems fail safely. |
| 2 | LibreOffice clobbers preserved output | Private staging and isolated Office profile; exact nonempty expected output; commit only the selected destination. |
| 3 | Update failure deletes existing file | Unique partial download, bounded streaming, digest/length validation, atomic final commit; cleanup only owned partials. |
| 4 | aria2 never completes | Monitor owned RPC queues, metadata children, and stable terminal states; explicit shutdown and bounded process reaping. Real local HTTP integration test added. |
| 5 | Windows CI masks native failures | PowerShell 7 steps explicitly stop on native failures. A workflow contract test checks every PowerShell step. |
| 6 | Debian Beta sorts before Alpha | Debian epoch `1:0.5.0~beta`; filenames remain versioned without the epoch. Stable `1:0.5.0` still sorts after Beta. |
| 7 | UI dispatch stops after one error | Isolate each callback, always reschedule, cap each tick at 200 items / 15 ms. |
| 8 | Cleared exception captures | Bind stable error strings; include both large runtime files in correctness lint. |
| 9 | Invalid WebM codecs | VP9 / Opus selection; real app-engine FFmpeg/FFprobe round trip. |
| 10 | Pandoc takes unsupported jobs | Explicit input/output capability routing; Office fallback for eligible formats; meaningful failure when no compatible backend produces output. |
| 11 | Unsupported .7z promise | Removed .7z from in-app recognized archive inputs; backend center and guide explicitly identify 7-Zip as an external app. Native in-app 7z support is not claimed. |
| 12 | Windows installer elevation/mutex | Elevation-capable ShellExecute `runas`, failure handling, updater shutdown after successful handoff. Real UAC accept/cancel and installed-app handoff still need manual validation. |
| 13 | Portable ZIP misses updater | Portable ZIP now includes the updater; signing verification includes the staged portable updater. |
| 14 | Wrong-platform update selection | Removed generic fallback predicates; require matching OS and architecture, otherwise use the release page. |
| 15 | Compatibility is display-only | Enforce rejection before download and installation; examples no longer advertise Windows assets for Linux or use valid-looking fake hashes. Example manifests are not fetched as production fallbacks. |
| 16 | Failed queue rows disappear | Remove only successful rows; retain failed/canceled items; snapshot inputs/options before worker launch; explicit error/stopped status. |
| 17 | Zero checks reported as success | Strict hash/report validation; reject empty/malformed input; GNU binary marker and report-relative paths supported. |
| 18 | Blocking hashing / cancellation gaps | Verification runs in a worker; hash and archive streaming check cancellation in bounded chunks. |
| 19 | ZIP includes itself | Enumerate before staging; exclude output; reject source/output identity and duplicate member names; staged commit. |
| 20 | Extraction overwrites edits | Validate and extract privately, publish into a new destination; existing destinations are preserved. |
| 21 | Redirect trust gap | Policy-aware redirect handler in updater and main-app update paths; HTTPS/host/userinfo validation and metadata/download limits. |
| 22 | Unauthenticated RPC | Random per-session secret, explicit no-conf mode, loopback binding, secret redaction from logged commands, stop-with-parent protection. |
| 23 | RPC error looks like pause success | Validate JSON-RPC envelope/id/result; pause/resume runs off the UI thread and changes state only after acknowledgement; file-selection mutation is blocked during transfers. |
| 24 | Trusted signing absent | External blocker remains. Unsigned local development builds are clearly not release-ready. Public tagged builds still fail closed. |
| 25 | Native license/source obligations | Collect actual installed dependency notices and frozen native hashes; disclose bundled FFmpeg. Public publication additionally requires completed legal/source/consumer-terms review. Notices alone do not close this blocker. |
| 26 | Beta docs ahead of public assets | README separates development Beta from verified public Alpha; offline site uses neutral release-list language and only shows real alternative assets; static links work without JS. |
| 27 | Runtime absent from lint gates | Main/updater and new helpers included in lint; four additional helpers strictly type-checked; application-engine/RPC integration tests added. |
| 28 | Drifting Linux / missing PR builds | Pin Ubuntu 24.04 packaging and enable pull-request builds. Hosted execution remains unverified until these local changes are pushed. |
| 29 | Requirements-only SBOM | Generate full installed-environment CycloneDX evidence on both OSes plus per-platform hashes of frozen native payloads. Build dependencies are explicitly distinguished from shipped payload evidence. |
| 30 | Dialog on every output | Unused names proceed directly; safe numbered names on conflicts by default. Settings opt-in restores explicit per-file conflict decisions. |
| 31 | Narrow layout testing | Persistent primary-action/Stop footer; expanded compact/scaled/theme/settings/first-run/updater probes, including setup acceptance. Physical Wayland, Windows GUI/UAC, Narrator/Orca, and full keyboard traversal remain manual checks. Three-tier navigation was not rearchitected. |
| 32 | Website invisible on API delay | Content visible without JS; reveal enhancement independent of fetch; abort after five seconds; real static release/repository links. |
| 33 | Debian metadata incomplete | Installed-Size, Homepage, and explicit Ubuntu-baseline GUI runtime dependencies added. Extracted-package smoke checks are not a substitute for a clean physical/VM install. |
| 34 | Overbroad compatibility claims | Known Windows targets separated from newer best-effort versions; Ubuntu 24.04 build baseline separated from other releases; reject unknown required backend versions; normalize architecture aliases. |
| 35 | Monolithic maintenance boundaries | Extract file commits, checksum verification, archive streaming, and update transport; reuse RPC lifecycle helpers. Incremental boundaries, not a claim that the entire application has been rewritten or fully typed. |

## Dependency Updates

- pillow-heif: 1.4.0 -> 1.8.0
- PyInstaller: 6.20.0 -> 6.22.3
- Ruff: 0.15.22 -> 0.16.9
- mypy: 2.3.0 -> 2.3.1
- cyclonedx-bom: 7.3.0 -> 7.4.0

Versions were checked against PyPI during this pass. Installed in project-local
Windows/Linux virtual environments, not into the system Python environment.

## Verification Evidence

### Final Local Results

| Check | Result |
| --- | --- |
| Windows unit suite, Python 3.11.9 | 105 discovered: 97 passed, 8 gated backend tests skipped. |
| Ubuntu 24.04 / WSL unit suite, Python 3.12.3 | 105 discovered: 97 passed, 8 gated backend tests skipped. |
| Separately enabled Linux native-backend integration suite | All 8 passed, including actual application WebM conversion and aria2 completion/cleanup. |
| Linux Xvfb layout probes | All 17 passed; compact/scaled/theme layouts, first-run acceptance, settings, and updater included. |
| Correctness lint and targeted typing | Ruff passed; mypy passed for 15 shared/helper files and 4 submission-tool files. |
| Website | JavaScript syntax and release-contract tests passed. |
| Application dependency vulnerability audit | No known vulnerabilities reported for `requirements.txt` on either OS at test time. This is not a native-binary security certification. |
| Windows build | App, updater, installer, and portable ZIP built successfully; frozen smoke/performance checks passed. Portable ZIP contains its updater. |
| Linux build | .deb, AppImage, and tarball built successfully with no active venv. The existing repo-local venv was reused, so this was not a fresh-venv/clean-clone trial. |
| Linux package isolation | Extracted .deb, AppImage extract-and-run, and tarball passed CLI version/smoke checks from outside the source tree with temporary user directories. No host package installation was performed. |
| Package integrity | All 7 versioned deliverables matched the Windows/Linux SHA256SUMS files. |
| Debian upgrade ordering | `1:0.5.0~beta` sorts after Alpha `1.8.17` and before stable `1:0.5.0`. |
| Release readiness | Not approved for publication: local Windows installer is unsigned; external release gates below remain open. |

Final frozen smoke timings were approximately 1.98 s for the Windows one-file app,
1.02 s for its updater, 0.90 s for the portable app, 2.42 s for the Linux app,
and 0.78 s for the Linux updater. These are local CLI smoke measurements, not
interactive first-launch latency on consumer hardware.

### Generated Artifacts

The final local candidates are in `release_bins/`:

- `FormatFoundry_Setup_0.5.0-beta.exe`
- `FormatFoundry_0.5.0-beta.exe`
- `FormatFoundry_Updater_0.5.0-beta.exe`
- `FormatFoundry_Portable_0.5.0-beta_windows_x86_64.zip`
- `format-foundry_0.5.0-beta_amd64.deb`
- `FormatFoundry_linux_0.5.0-beta_x86_64.AppImage`
- `FormatFoundry_linux_0.5.0-beta_x86_64.tar.gz`

The preexisting numeric transport tag remains a migration detail; no new tag was
created and no remote release was modified in this pass.

### Evidence Files

Local evidence is under `build/` (ignored generated files, not committed source):

- `remediation-tests-windows.log` and `remediation-tests-linux.log`
- `remediation-backends-linux.log`
- `remediation-ui-linux/layout-probe.json` and matching PNG captures
- `remediation-windows-build-final.log` and `remediation-linux-build-final.log`
- `remediation-linux-package-checks.log` and `remediation-quality-linux.log`
- `remediation-performance-windows.json` and `remediation-performance-portable-windows.json`
- `remediation-performance-linux.json`
- `remediation-pip-audit-windows.json` and `remediation-pip-audit-linux.json`
- `FormatFoundry-SBOM-windows.cdx.json`, `FormatFoundry-SBOM.cdx.json`
- `native-payload-windows.json`, `native-payload-linux.json`

Do not interpret passing unit tests, Xvfb probes, or frozen CLI smoke tests as proof
that every consumer workflow or real desktop install has been exercised. The
expanded probe tests action/footer reachability and setup acceptance, not a full
screen-reader or all-module keyboard audit.

## Release Gates Still Requiring Human Evidence

1. Provision a trusted Windows signing identity through the existing OIDC or PFX flow in `docs/WINDOWS_SIGNING.md`. No self-signed certificate is substituted for publisher trust.
2. Complete the exact bundled-native license/corresponding-source review and consumer-use terms. Only then set repository variable `RELEASE_LICENSE_REVIEWED=true`.
3. Install the candidate .deb on a real clean Ubuntu 24.04 desktop, launch it from the desktop launcher without the source folder, test its updater/settings and AppImage, and record the tested commit. Set `UBUNTU_VALIDATED_COMMIT` to that exact commit SHA only after it passes.
4. Push the reviewed changes and require hosted Windows/Linux package CI to pass before tagging. The local audit does not assert that GitHub checks have run on unpushed work.

The release assembly gate checks both review variables; normal PR/development
builds remain available without them. Existing public Alpha downloads are unchanged.

## Backup And Safety

Before edits, source was archived outside the checkout at
`D:/Codex/Format Foundry Archives/audit-remediation-2026-09-26/source-before-remediation.zip`.
Original release files are preserved beside it in `release_bins-before/`.
The source archive SHA256 is
`9A47BD0398D33B24D253D43AE1CE309DA3F32C14C959A1D19B5FDA5406EB82C7`.
Build snapshots remain available under the existing archives/history directory.
Final test/build logs, UI captures, package checksum lists, SBOMs, and native-payload
inventories are preserved alongside the original backup as `verification-evidence.zip`.
The snapshot script now excludes the Windows venv, env files, and signing-key files
at the project root rather than copying them into new source snapshots.

## Technical References

- [PowerShell native error handling](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_error_handling?view=powershell-7.6)
- [Debian control fields and version epochs](https://www.debian.org/doc/debian-policy/ch-controlfields.html)
- [aria2 RPC manual](https://aria2.github.io/manual/en/html/aria2c.html#rpc-interface)
- [FFmpeg licensing guidance](https://ffmpeg.org/legal.html)

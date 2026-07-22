# Format Foundry OpenAI Build Week Audit

Audit created: 2026-07-18
Last updated: 2026-07-22
Product: Format Foundry Beta 0.5 (`0.5.0-beta`)
Repository: `https://github.com/Pugmaster04/Format-Foundry`
Track: Work & Productivity
Submission period: 2026-07-13 09:00 PT through 2026-07-21 17:00 PT

## Purpose

Format Foundry existed before the submission period. This audit separates the prior project from
meaningful Build Week extensions, records repeatable verification, and keeps unresolved submission
requirements visible. It is evidence support, not a substitute for the official rules or entrant
eligibility representations.

## Pre-Existing Baseline

- The project, its conversion modules, and earlier Alpha releases existed before July 13, 2026.
- All historical releases below Beta 0.5 remain classified as Alpha in `CHANGELOG.md`.
- Build Week judging should focus on dated work added after the submission period opened.

## Build Week Extensions

| Evidence | Date | Meaningful extension |
| --- | --- | --- |
| Commit `3cc840ea24cb96799f68bb8eab1d7a9847229d00` | 2026-07-18 | Prepared the Beta 0.5 consumer release, installer/updater hardening, responsive UI, package validation, and release contracts. |
| Current Build Week worktree | 2026-07-18 | Added managed Windows signing phases, provenance identity, GitHub artifact attestations, privacy-safe path display, submission media, and this audit ledger. |
| `submission-media/MEDIA_MANIFEST.json` | 2026-07-18 | Binds authentic captures and upload-ready images to exact dimensions, SHA-256 hashes, and the project provenance ID. |
| `docs/PROVENANCE.md` | 2026-07-18 | Documents embedded project identity, release manifests, checksum verification, and GitHub attestation verification. |
| `addons/idea_bank.py` and `docs/OPTIMIZATION_AUDIT.md` | 2026-07-18 | Add an opt-in local planning workspace and a screenshot-backed cross-platform optimization review. |
| `addons/pc_health.py` and cross-platform build evidence | 2026-07-18 | Add an opt-in, read-only PC health workspace and verify native Ubuntu packages plus six real backends. |

The Build Week worktree was not committed before the stated July 21 deadline. A commit created after
that deadline must not be backdated or represented as proof that these files were publicly submitted
on time. File timestamps, this ledger, and local build evidence support the development record but do
not replace the official submission timestamp or rules.

## Post-Period Maintenance

On 2026-07-22, the interrupted task resumed to finish documentation, add an authentic PC Health
gallery slide, refresh media provenance, and prepare a protected Git branch. These changes are
recorded transparently and are not claimed as submission-period work.

## Verification Record

| Check | Result |
| --- | --- |
| Python compilation | Passed for app, updater, provenance, audit, and media scripts |
| Python unit tests | 80 discovered; 74 passed in the regular gate and 6 real-backend tests were explicitly skipped there |
| Ubuntu real-backend integration | 6 of 6 passed: FFmpeg/FFprobe, Pandoc, LibreOffice, 7-Zip, ImageMagick, and aria2 |
| Ruff and strict mypy | Passed for shared foundations, backend/runtime seams, add-ons, and quality tools |
| Dependency audit and SBOM | No known dependency vulnerabilities; reproducible CycloneDX SBOM generated |
| Website release contract | Passed |
| GitHub workflow YAML parse | Passed |
| Fresh Windows PyInstaller app build | Passed |
| Fresh Windows PyInstaller updater build | Passed |
| Fresh Windows Inno Setup installer build | Passed; versioned Beta 0.5 assets and checksums staged |
| Frozen `--provenance` checks | Passed for app and updater |
| Frozen headless startup checks | Passed for app and updater on Windows AMD64 |
| Responsive UI matrix | Eight Windows and eight Linux/Xvfb cases passed, including 1024x768 and 1280x720 at 150% |
| Submission media validation | 14 PNG assets passed dimensions, provenance metadata, and hash checks |
| Devpost media ZIP | 26 deterministic entries passed archive integrity testing; cache files excluded |
| Linux package validation | Clean `.venv` bootstrap, frozen binaries, Debian package, AppImage, tarball, AppStream metadata, layout, and checksums passed |

Media archive SHA-256:
`320093f21c32e1b7d448083767a2e7d086cedb50a32d6ed7be51740302a0d0f7`

## Submission Compliance

| Requirement | Evidence | Status |
| --- | --- | --- |
| Meaningfully extend a pre-existing project during the submission period | Commit, current diff, changelog, ledger | Local evidence exists; official on-time submission status cannot be inferred from this audit |
| Working project matching its description | Windows and Ubuntu builds, package tests, and smoke tests | Locally verified; trusted tagged publication and physical Ubuntu desktop check remain |
| Codex collaboration | Repository diff and hash-chained events | Session ID and exported/timestamped task evidence still required |
| GPT-5.6 contribution | Must identify the real contribution and resulting artifact | Pending truthful model evidence |
| README explains Codex and GPT-5.6 collaboration | Public README | Codex work and the absence of a verified GPT-5.6 artifact are disclosed truthfully |
| Public YouTube demo under three minutes with audio | `submission-media/VIDEO_STORYBOARD.md` | Storyboard ready; recording and public URL pending |
| Code repository available for judging | Public GitHub repository and proprietary license | Verify final pushed commit and judge access before submission |
| `/feedback` Codex Session ID | Devpost form | Pending entrant action in the core Codex task |
| Test build available without rebuilding | Versioned EXE, DEB, AppImage, tarball, and portable ZIP release contract | Pending final trusted signed/tagged publication |
| Third-party rights and notices | `THIRD_PARTY_NOTICES.txt` and backend separation | Final media/music/trademark review pending |

## Evidence Still Needed

1. Commit and push the current work with its real post-deadline timestamp; do not backdate it.
2. Preserve proof of any official Devpost submission that was actually completed before the deadline.
3. Record the actual GPT-5.6 contribution only if it occurred and point to its resulting artifact.
4. Obtain the core Codex Session ID only through the required `/feedback` flow.
5. Configure a trusted Windows signing identity, run tagged CI, and preserve workflow and attestation URLs.
6. Complete a physical Ubuntu install/launch/uninstall check from the final Debian package and AppImage.
7. Add the public narrated demo URL only if a compliant video was actually published.

## Chain Verification

Run:

```text
python tools/hackathon_audit.py verify
```

The current chain head and evidence-file hashes are recorded in `AUDIT_SNAPSHOT.json`.

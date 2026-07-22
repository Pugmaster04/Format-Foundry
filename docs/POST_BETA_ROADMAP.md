# Post-Beta Roadmap

This document records the work that follows the `Beta 0.5` hardening pass. It is ordered by release risk so product improvements do not bypass distribution, security, or accessibility gates.

## Current readiness

Validated on 2026-07-22:

- Windows installer completed a clean, isolated install; displayed the first-run wizard; launched the app and updater; passed both smoke modes; and removed binaries, registration, and Start menu entries during uninstall.
- Ubuntu 24.04 `amd64` installed the Debian package, displayed the first-run, app, and updater windows under an isolated display, ran without the source tree, validated AppStream metadata, and uninstalled cleanly.
- The AppImage passed version, smoke, and GUI-window checks without installation.
- Windows installer, Windows portable ZIP, Linux tarball, Debian package, and AppImage now carry local license terms. The Debian package provides `/usr/share/doc/format-foundry/copyright`.
- Machine-readable local evidence is written to `build/final-validation/windows-consumer-acceptance.json` and `build/final-validation/linux-consumer-acceptance.json`.

## Release blocker

A public Windows Beta release remains blocked until a publicly trusted signing identity is configured.

The protected GitHub environment `windows-release-signing` exists, but currently has no signing secrets or variables. The development machine has no code-signing certificate and no Azure CLI configuration. Tagged release CI must continue to fail closed under these conditions.

Acceptable paths are:

1. Configure Azure Artifact Signing with GitHub OIDC and the environment variables documented in `docs/WINDOWS_SIGNING.md`.
2. Configure a CA-issued code-signing PFX through the documented encrypted GitHub secret fallback.

Do not publish a self-signed installer as a trusted public release and do not weaken signature verification to unblock publication.

## Work order

### P0: Trusted release identity

- Provision one supported signing path.
- Run the tagged workflow without publishing first, where possible.
- Verify Authenticode on the app, updater, portable executable, and installer.
- Confirm checksums, SBOMs, provenance, and GitHub attestations bind to the same source commit.
- Publish only after Windows and Linux consumer acceptance passes against the exact release artifacts.

Completion criteria: the release workflow produces verified signed Windows artifacts and all advertised versioned download URLs resolve.

### P1: Main application modularization

- Extract shared shell, responsive layout, settings, status, and dialog primitives from `modular_file_utility_suite.py` without changing workflows.
- Move one module family at a time behind narrow interfaces and preserve current tests after each move.
- Keep backend execution outside Tk event handlers and isolate UI state from task state.

Completion criteria: module files are independently testable, no feature regresses, and startup/performance budgets remain green.

### P1: Clean-device compatibility matrix

- Add repeatable Windows 11 clean-VM installer, first-run, updater, and uninstall checks.
- Add a real Ubuntu 24.04 desktop launcher, first-run, updater, AppImage, and uninstall sign-off outside WSL.
- Record display sizes, scaling, desktop environment, OS build, package version, and artifact hashes.
- Keep Ubuntu 24.04 `amd64` as the validated Linux baseline until another distribution completes the same matrix.

Completion criteria: consumer paths pass on clean devices with no Codex checkout, Python environment, or optional backends preinstalled.

### P1: Updater and backend resilience

- Exercise missing, outdated, incompatible, and partially installed backend states on both platforms.
- Keep installation commands allowlisted and platform-specific.
- Improve recovery messaging for package-manager failures without claiming the app can repair system repositories.
- Add compatibility fixtures for backend version-output changes and operating-system lifecycle updates.

Completion criteria: every feature clearly reports required backends, safe install choices, detected versions, and actionable recovery steps.

### P2: Long-running workflow consistency

- Apply the shared cancellable-task model to remaining long operations.
- Make pause, resume, cancel, and terminal states consistent across modules.
- Virtualize large queue, file, and analysis result views to avoid rendering every row at once.

Completion criteria: long operations do not block the UI, cancellation is bounded, and large datasets remain responsive.

### P2: Accessibility sign-off

- Complete keyboard-only navigation checks on Windows and Linux.
- Run manual Narrator and Orca passes.
- Verify 1024x768, 1280x720 at 150% scaling, and common desktop resolutions in light, dark, high-contrast, and reduced-motion modes.
- Confirm focus order, labels, scroll boundaries, minimum target sizes, and dialog resizing.

Completion criteria: no required action is hidden, pointer-only, or dependent on animation.

### P2: Optional add-on boundary

- Keep Idea Bank and PC Health Snapshot disabled by default and locally contained.
- Do not enable third-party add-on loading until signed manifests, version compatibility, explicit consent, isolation, and removal behavior are implemented.
- Define a stable built-in add-on interface before adding another optional workspace.

Completion criteria: optional features can be enabled, disabled, upgraded, and removed without affecting core conversion workflows or user data.

## Change discipline

- Keep one canonical product/package version across app, updater, installer, package metadata, website, and release assets.
- Add contract tests before changing public artifact names or download URLs.
- Preserve signed-release and checksum verification gates.
- Keep generated artifacts and machine-local acceptance data out of source changes unless they are intentionally published as release evidence.
- Complete one bounded roadmap item per pull request when practical.

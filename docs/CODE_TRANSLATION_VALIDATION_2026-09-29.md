# Code Translation Validation

Date: 2026-09-29. Scope: unreleased Beta 0.5 source changes.

## Implemented

- The Code Languages tab can generate JavaScript from one `.ts`, `.mts`, or `.cts` file using the official TypeScript compiler. Corresponding outputs are `.js`, `.mjs`, and `.cjs`.
- The Code Languages tab also compiles a local TypeScript project using its `tsconfig.json`. Imports and local configuration inheritance are handled by `tsc`; generated JavaScript is delivered in a ZIP rather than written into the source tree. This does not install or bundle project dependencies.
- Both adapters require native Node.js and TypeScript. Consumer packages do not bundle those tools; the tab shows setup guidance when they are absent. The 21-profile rules library and read-only inspection remain available without them.
- Input is limited to a regular UTF-8 file of at most 64 KiB. Compilation has a 25-second limit and can be canceled. Compiler errors do not create an output file. Generated output is capped at 512 KiB and committed without replacing an existing file.
- Project compilation stages at most 256 regular source/configuration files (4 MiB combined; 512 KiB per file) and caps generated output at 8 MiB. It skips dependency/build directories, rejects symlinks and project references, rejects configuration paths outside the project, and enforces a 60-second limit per compiler pass. Failures and cancellation leave no output ZIP. Existing ZIPs are never replaced.
- The compiler runs against a temporary copy, not the user's source path. The app previews the generated JavaScript but does not execute it or claim behavioral equivalence.
- The repository pins TypeScript 5.9.3 for tests. Windows release/build and Ubuntu quality/build CI jobs install that test compiler and fail if the adapter cannot detect it. Their real-compiler tests must therefore run rather than silently skip.

## Local Checks

| Check | Result |
| --- | --- |
| Windows full Python suite in pinned build environment | 193 tests, no failures; 9 skipped |
| Disposable Ubuntu 24.04 WSL QA full suite after package install | 186 tests, no failures; 11 skipped |
| Windows real TypeScript compiler tests | Passed: single-file emit, ESM/CommonJS syntax and `node --check`, project imports and `tsconfig.json`, local configuration inheritance, type errors, unsafe configuration rejection, source preservation, and no source execution |
| Windows hidden-Tk Code Languages tests | Passed, including both file and project feedback, cancellation, and source preservation |
| Smaller-monitor visual layout probe | Passed at 1024x768/100% and 1280x720/150% on DISPLAY2 with `--no-activate`; both translation actions were reachable by scrolling. Evidence: `build/translation-validation/ui-layout-secondary/layout-probe.json` and matching screenshots. |
| Windows and WSL full CI-scope Ruff | Passed |
| Windows and WSL dependency-light mypy | Passed for 17 source files, plus 4 submission-media source files |
| Windows source performance budget | Passed: main import 0.2309 s / 1.5 s; updater import 0.1660 s / 1.0 s; backend detection 0.1516 s / 3.0 s |
| Repository integrity | Passed |

The WSL QA distribution has no native Node.js compiler. Its adapter tests and hidden-Tk tests ran, while the real-compiler test class skipped. Ubuntu CI installs native Node.js and the pinned compiler before testing, with an explicit detection assertion. This CI change has not yet run on GitHub for this source state.

## Boundary

- This is a verified TypeScript-to-JavaScript path, not a syntax-substitution engine for all 21 languages. Other translation pairs remain disabled until they have separately tested adapters and behavior checks.
- Single-file compilation deliberately rejects imports requiring a project build; project compilation is the path for local imports and `tsconfig.json`. It is not a package manager or bundler: external dependencies must already be available to the compiler, and a successful compiler exit does not prove equivalent runtime behavior.
- The Windows visual probe ran on the secondary 1920x1080 monitor without activating the app window. This verifies layout and action reachability, not end-to-end installer behavior.
- Windows EXE and installer, Linux `.deb`, AppImage, and tarball were rebuilt locally. The Windows installer was uninstalled/reinstalled and the `.deb` was installed in disposable Ubuntu WSL QA; details are in `docs/INSTALL_VALIDATION_2026-09-29.md`. Nothing was published. A physical-Ubuntu GUI check, a version increment, and Windows signing remain release gates.
- The pre-edit snapshot of touched files is preserved at `build/translation-validation/before-translation-20260929-131941.zip` on this machine.
- A second pre-project-change snapshot is preserved at `build/translation-validation/before-project-translation-20260929-143009.zip`.

# Code Language Library Validation

Date: 2026-09-29. Scope: unreleased Beta 0.5 source changes only.

This records the earlier reference-library milestone. The later TypeScript-to-JavaScript implementation and its checks are recorded in [CODE_TRANSLATION_VALIDATION_2026-09-29.md](CODE_TRANSLATION_VALIDATION_2026-09-29.md).

## Implemented

- Workspace -> Development -> Code Languages, using the existing shared module shell, theme and scroll handling.
- 21 local profiles with ten core rule topics each, named baselines, original examples, extension hints, porting pitfalls and official-documentation links.
- Case-insensitive name/alias/extension/topic search and reference comparisons. Programming, shell, query, markup and stylesheet categories are distinct.
- Bounded 64 KiB UTF-8 source inspection. Python receives AST parsing only; other languages have no syntax parser. No selected source is executed, imported, rendered, uploaded, modified or added to reports/logs.
- Ambiguous extensions remain ambiguous. Binary, legacy-encoding, oversized and non-regular inputs are rejected. POSIX file opens use nonblocking mode to avoid a substituted FIFO hanging the worker on open.
- Inspection runs off the UI thread, errors appear inline, and completion does not overwrite a reference view the user has switched to.
- Validated 512 KiB maximum bundled JSON asset, independent of the working directory. Missing/corrupt assets disable only the new section.
- Main and portable application specs include the JSON asset; Linux uses the main spec. No new dependencies or backend installations.

## Verification

| Check | Result |
| --- | --- |
| Full Windows Python regression suite | 167 tests: 158 passed, 9 skipped, no failures |
| Full Ubuntu 24.04 WSL QA regression suite | 167 tests: 149 passed, 18 skipped, no failures |
| New language and hidden-Tk UI tests within those runs | Windows: 31 passed, 1 POSIX-only skip; Linux: all 32 passed |
| Python compilation | Passed for main app and language helper |
| CI-scope Ruff lint | Passed, including main app, updater, helpers, add-ons and tests |
| CI-scope dependency-light mypy | Passed for 16 source files |
| Repository required-file verification | Passed |
| Git whitespace check | Passed; existing line-ending normalization warnings remain |
| Source performance budget | Passed: main import 0.1391 s / 1.5 s; updater import 0.1026 s / 1.0 s; backend detection 0.1154 s / 3.0 s |
| Isolated PyInstaller one-file library probe | Built and executed successfully: 21 profiles, revision 2026-09-29.1 |

Windows skips were eight opt-in real-backend integration tests and the POSIX FIFO test. PDF tests used the previously staged PDFium runtime under `build/adobe-validation/pdf-runtime`; this did not install or alter system dependencies.

Linux used the existing disposable `FormatFoundry-QA-20260926` WSL distribution, not the user's primary distribution. Skips were eight opt-in real-backend tests, nine PDFium-dependent tests and one ImageMagick-dependent test. All new language tests, including hidden Tk interactions and FIFO rejection, passed there.

The frozen probe asserts that its asset path is inside PyInstaller's extraction directory, not the source checkout. It was launched with the validation directory as its working directory. This verifies the new helper/data packaging mechanism, not an end-to-end rebuild of consumer installers.

Evidence is in the ignored local directory `build/language-library-validation/`:

- `full-regression.log`
- `linux-full-regression.log`
- `performance.json`
- `frozen-build.log`
- `frozen-runtime.json`
- `dist/LanguageLibraryProbe.exe` (test helper, not the application)
- `before-language-library-20260929-124745.zip` (pre-edit snapshot of touched existing files)

## Boundaries

- This is a curated reference foundation, not a complete grammar/specification, language server, compiler, AI model or cross-language translator.
- Python AST success does not prove compilation in every context, type correctness, dependency availability, security or behavioral equivalence. It uses the Python version in the running build.
- No compilers were installed, and the examples were not executed across 21 languages. Examples and summaries require normal review as the supported baselines evolve.
- Official documentation fetch attempts failed due to network connection errors during this pass. The links are reference pointers, not a claim of live link verification or latest-spec synchronization.
- Tk tests constructed withdrawn windows and exercised controls; no visible, screenshot-backed theme/scaling or physical-Linux-desktop validation was performed in this pass.
- Existing EXE, Debian and AppImage releases were not rebuilt or published. Launching an older installed binary will not show this section until an application build includes these source changes.

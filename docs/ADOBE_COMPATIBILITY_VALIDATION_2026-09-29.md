# Adobe Interchange Validation

This is an unreleased source change, not a new installer or published release.
The working tree already contained unrelated audit remediation; those changes were preserved.

## Implemented Scope

- PDF and PDF-compatible Illustrator AI: PDF document export, all-page TIFF, first-page PNG/JPEG at 150 DPI.
- Photoshop PSD: 8-bit saved RGB/CMYK composites through Pillow, broader variants through ImageMagick where supported.
- Photoshop PSB: saved composite through ImageMagick; no layer editing or editable project export.
- Multipage TIFF: all pages retained when exporting PDF in PDF / Documents.
- Images pipeline: first page/frame only; input-only PDF/AI/PSD/PSB default to PNG when `keep` is selected.
- PDF metadata inspection reports document page count instead of incorrectly calling the file an unrecognized image.
- Malformed/legacy PostScript AI and unsupported native project formats receive explicit errors.
- PDF import is bounded and serialized around PDFium. No form/JavaScript initialization or PostScript policy changes were added.
- PDF, image-to-PDF and ImageMagick output use temporary staging and existing collision-aware commit helpers.

## Verified Results

| Check | Result |
| --- | --- |
| New Adobe-specific tests on Windows | 26 passed with the local PDFium runtime available. |
| Complete unittest discovery on Windows | 135 discovered: 127 passed, 8 pre-existing opt-in backend integration tests skipped. |
| Real TaskEngine conversions | 14 passed: PDF, PDF-backed AI, TIFF, PSD and PSB to their supported PDF/raster targets. |
| Actual multipage output | Both PDF pages decoded from resulting TIFF; TIFF-to-PDF retained two pages. |
| Frozen Windows renderer probe | PyInstaller onedir EXE ran from outside the repository cwd and rendered a two-page PDF to a two-frame TIFF. Native pdfium.dll and runtime data were bundled. |
| Ubuntu 24.04 WSL source tests | 26 discovered: 16 passed, 10 skipped because PDFium and ImageMagick are not installed in the disposable QA environment. |
| Compilation / Ruff | Passed for the new helper, changed app, tests and notice collector. |
| Performance budgets | Passed: main import 0.1464 s, updater import 0.1119 s, backend detection 0.1246 s on this host. |
| Fixture integrity | 107 registered fixtures and 112 offline catalog links verified; 101 valid fixtures plus 6 intentionally invalid/unsupported cases. |

## Environment And Evidence

Windows application source tests used the existing Python 3.11 project environment.
The already installed pypdfium2 5.13.0 runtime was staged under `build/adobe-validation/pdf-runtime`
for isolated tests, because HTTPS verification to package/documentation sites failed on this PC.
No TLS checks were bypassed. The application contains no Codex runtime paths.
The normal source/build dependency is pinned in requirements.txt and frozen app specs explicitly include PDFium.

The Ubuntu checks ran in the existing disposable `FormatFoundry-QA-20260926` WSL distro, not the user's primary Ubuntu distro.
The pure-Python packaging library was provided only through a test PYTHONPATH for the license-collector test;
no system package installation or production app replacement was performed.

Local evidence:

- `D:/Format-Foundry-Test-Files/_validation/adobe-full-with-pdfium.log`
- `D:/Format-Foundry-Test-Files/_validation/adobe-linux-tests.log`
- `D:/Format-Foundry-Test-Files/_validation/adobe-conversions.json`
- `D:/Format-Foundry-Test-Files/_validation/adobe-frozen-result.json`
- `D:/Format-Foundry-Test-Files/_validation/adobe-frozen-build.log`
- `D:/Codex/Format-Foundry/build/adobe-validation/performance.json`

The source backup before this pass is
`D:/Format-Foundry-Test-Files/_validation/before-adobe-support-20260929-120753.zip`.

## Sample Authenticity

The PSD and PSB fixtures are synthetic, correctly structured uncompressed Photoshop composites,
not renamed PNGs. Their pixels were decoded by Pillow/ImageMagick and converted by TaskEngine.
The AI fixture explicitly exercises the PDF-compatible container path using a real PDF under an AI extension.
It is not an Illustrator-authored editable project or evidence for arbitrary Illustrator private data.
No personal RAW photos were used for the Adobe tests or uploaded anywhere.

## Remaining Gates

- Full Windows installer and Linux .deb/AppImage have not been rebuilt for these changes.
- The isolated frozen renderer is not proof of the entire packaged app, updater or GUI workflow.
- Install the pinned renderer through the standard build dependencies, then validate actual packaged PDF/AI conversion on Linux.
- Run dependency vulnerability auditing and hosted CI when verified network access is available.
- Obtain representative Illustrator-authored PDF-compatible files and layered/advanced Photoshop files for wider compatibility testing.
- No claims of editable layers, vectors, spot-color fidelity, native InDesign/Premiere/After Effects editing, OCR or PDF-to-Word conversion are made.

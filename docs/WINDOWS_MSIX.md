# Windows MSIX and Microsoft Store

Microsoft Store MSIX is the planned Windows distribution path for Beta 0.7.1.
The app remains a desktop Tk application with normal access to user-selected files.
Microsoft signs the submitted package after certification; a publisher PFX is not
needed for this channel. The package is not yet certified or available in the Store.
Linux `.deb` and AppImage packaging continues through GitHub releases.

## Build from a clean Windows clone

Install Python 3.11 or newer (3.12 recommended) and the [Windows 11 SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/),
including its packaging tools. Run from the repository root:

```powershell
.\build_msix.ps1
```

The script creates/reuses `.venv-windows`, installs the pinned build dependencies
there, freezes the app and optional-tools updater into one folder, and uses the SDK's
MakeAppx tool. No Inno Setup, signing certificate, Codex installation, or installed
feature backend is needed to build the MSIX.

Outputs for the current version:

- `release_bins/msix/FormatFoundry_0.7.1-beta_x64_development.msix`
- `release_bins/msix/FormatFoundry_0.7.1-beta_x64_development.validation.json`
- `release_bins/msix/SHA256SUMS-msix-candidate`

The development package uses a separate `FormatFoundry.Development` identity and
the Windows unsigned-test OID. It is for local testing, not public installation or
Store submission. MakeAppx validates the manifest; the builder verifies every payload
block hash, x64 executables, required resources, and logo dimensions. It unpacks the
result and runs both frozen startup probes from an unrelated working directory.

For an already frozen payload, use `-SkipFreeze`. A source/resource fingerprint
rejects stale payloads; rebuild without that option after source changes.
`-PythonPath` selects an explicit build interpreter.

## Installed development-package test

Windows 11 permits unsigned package testing with `Add-AppxPackage -AllowUnsigned`.
Run this in an administrator PowerShell after building:

```powershell
.\tools\test_msix_install.ps1 `
  -PackagePath .\release_bins\msix\FormatFoundry_0.7.1-beta_x64_development.msix
```

This registers only the separate development identity, checks the installed app
and updater with their real Windows package identity and private settings path,
then removes that package. It refuses to replace an existing development package.
It does not add a certificate or change Developer Mode or Windows security settings.
The report is `build/msix/installed-validation.json`.

This headless test does not substitute for opening the registered app from Start,
using representative conversion/backends, and checking update/uninstall controls.
Use Windows App Certification Kit on the installed test package before submission;
record its results and any failures. Only Microsoft can grant Store certification.

## Reserve and build the Store product

1. [Create a Microsoft Store developer account](https://learn.microsoft.com/windows/apps/publish/partner-center/open-a-developer-account?tabs=individual)
   and reserve **Format Foundry** in Partner Center (or an available display name).
2. Open the app's **Product management -> Product identity** page. Copy the exact
   Package/Identity/Name, Package/Identity/Publisher, PublisherDisplayName, and Store
   product ID into `packaging/windows/store-identity.json`, using
   `store-identity.example.json` as the schema. These are public product identifiers;
   do not put account passwords, tokens, or signing keys in this file.
3. Build the submission package:

```powershell
.\build_msix.ps1 -Mode Store -IdentityFile .\packaging\windows\store-identity.json
```

This produces `FormatFoundry_0.7.1-beta_x64_store.msix` and its validation report.
The Store package uses the assigned identity and omits the unsigned-test OID. Store
mode rejects missing identities and example placeholders. Upload this unsigned
MSIX to the Partner Center **Packages** step; Microsoft signs it after certification.

The manifest targets x64 Windows desktop build 19041 or later. Actual certification,
hardware and OS validation determine the supported consumer audience. This package
is a desktop app with `runFullTrust`, not an AppContainer sandbox. Explain why access
to user-selected files and optional third-party tools is required in certification notes.
Optional backends remain optional, keep their own licenses, and must be clearly
described in the listing. Complete the existing bundled-license review before release.

### Version mapping

The app displays **Beta 0.7.1** and retains `0.7.1-beta` in filenames and metadata.
MSIX requires a four-part numeric version with a positive major and Store-reserved
final part `0`. The default maps `major.minor.patch` to `(major + 1).minor.patch.0`;
the current package is therefore **1.7.1.0**. This is a Windows package version,
not a change to the visible product version.

Never lower or reuse the Store version for an update. Promoting a Beta to a stable
release with the same numeric product version needs a higher explicit package
version, for example `-StoreVersion 1.7.2.0`. Keep that chosen sequence for later
builds. The fourth component is always `0` in submission builds.

## App lifecycle and migration

- App **Check Updates** and updater actions open Microsoft Store updates. They do
  not select or launch a GitHub EXE installer for a packaged installation.
- The included updater remains available for optional backend detection, install
  actions, and official links. Backends have their own installation and update lifecycle.
- **Uninstall** opens Windows Installed apps. It never selects an older EXE uninstaller.
- Both executables share `%LOCALAPPDATA%/Packages/<family>/LocalState/FormatFoundry`.
  Missing settings documents are copied once from the current or legacy EXE data
  folders. Originals remain intact, and existing package settings are preserved.
- Converted files stay in the user's output folder. Windows removes private package
  settings and history on uninstall; export them first if needed.
- EXE and Store installations are separate registrations. Install and validate the
  Store app before removing the older EXE through its own Windows entry. Close the
  older app before launching the package; the single-instance guard covers both.

## CI and publication

Branch and PR CI always builds an unsigned development candidate. It also builds
a Store submission when all four repository variables are set:

- `WINDOWS_STORE_PACKAGE_NAME`
- `WINDOWS_STORE_PUBLISHER`
- `WINDOWS_STORE_PUBLISHER_DISPLAY_NAME`
- `WINDOWS_STORE_PRODUCT_ID`

MSIXs, checksums and validation reports are downloadable CI artifacts. They are
not advertised as consumer direct downloads. No signing secrets are required.

Tagged coordinated releases require the real Store identity, the existing license
and Ubuntu validation gates, and these evidence gates:

- `WINDOWS_STORE_VALIDATED_COMMIT`: commit tested as an installed package.
- `WINDOWS_STORE_PUBLISHED_VERSION`: canonical version available through Store.
- `docs/windows-store.json`: `published: true`, the real product ID, and that package version.

Set those only after the corresponding checks pass. GitHub publishes Linux packages
and verification evidence. Windows users install and update through the Store;
unsigned submission/development MSIXs and EXE test builds remain CI artifacts.
The website reads `windows-store.json` and switches the Windows install buttons to
the Store listing only when it declares an approved published product.

References: [Store package requirements](https://learn.microsoft.com/windows/apps/publish/publish-your-app/msix/app-package-requirements),
[unsigned Windows 11 testing](https://learn.microsoft.com/windows/msix/package/unsigned-package),
[manual desktop packaging](https://learn.microsoft.com/windows/msix/desktop/desktop-to-uwp-manual-conversion).

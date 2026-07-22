import re
import unittest
from pathlib import Path

from app_identity import DISPLAY_VERSION, MIGRATION_RELEASE_TAG, PACKAGE_VERSION

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_TAG = MIGRATION_RELEASE_TAG


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


class ReleaseContractTests(unittest.TestCase):
    def test_app_updater_and_installer_versions_match(self) -> None:
        identity_source = read("app_identity.py")
        app_source = read("modular_file_utility_suite.py")
        updater_source = read("suite_updater.py")
        installer_source = read("installer/FormatFoundry.iss")
        self.assertIn(f'PACKAGE_VERSION = "{PACKAGE_VERSION}"', identity_source)
        self.assertIn(f'DISPLAY_VERSION = "{DISPLAY_VERSION}"', identity_source)
        self.assertIn("APP_VERSION = PACKAGE_VERSION", app_source)
        self.assertIn("APP_VERSION_LABEL = DISPLAY_VERSION", app_source)
        self.assertIn("CURRENT_VERSION = PACKAGE_VERSION", updater_source)
        self.assertIn("CURRENT_VERSION_LABEL = DISPLAY_VERSION", updater_source)
        self.assertIn(f'#define MyAppVersion "{PACKAGE_VERSION}"', installer_source)
        self.assertIn(f'#define MyAppDisplayVersion "{DISPLAY_VERSION}"', installer_source)

    def test_public_install_assets_are_versioned_consistently(self) -> None:
        readme = read("README.md")
        expected_assets = (
            f"FormatFoundry_Setup_{PACKAGE_VERSION}.exe",
            f"FormatFoundry_Portable_{PACKAGE_VERSION}_windows_x86_64.zip",
            f"format-foundry_{PACKAGE_VERSION}_amd64.deb",
            f"FormatFoundry_linux_{PACKAGE_VERSION}_x86_64.AppImage",
        )
        for asset in expected_assets:
            self.assertIn(asset, readme)
        self.assertIn("/releases/latest", readme)
        self.assertNotIn(f"/releases/download/v{PACKAGE_VERSION}/", readme)

    def test_alpha_to_beta_transport_contract_is_consistent(self) -> None:
        identity = read("app_identity.py")
        runtime = read("support_runtime.py")
        manifest = read("update_manifest.example.json")
        site = read("docs/site.js")
        workflow = read(".github/workflows/cross-platform-build-release.yml")
        self.assertIn(f'MIGRATION_RELEASE_TAG = "{TRANSPORT_TAG}"', identity)
        self.assertIn("RELEASE_TRANSPORT_TAG = MIGRATION_RELEASE_TAG", runtime)
        self.assertIn(f'"latest_version": "{TRANSPORT_TAG}"', manifest)
        self.assertIn(f'"release_tag": "{TRANSPORT_TAG}"', manifest)
        self.assertIn(f'const fallbackReleaseTag = "{TRANSPORT_TAG}"', site)
        self.assertIn("detectPackageVersion", site)
        self.assertIn("steps.prep.outputs.package_version", workflow)

    def test_tagged_windows_release_fails_closed_without_signatures(self) -> None:
        workflow = read(".github/workflows/cross-platform-build-release.yml")
        build_script = read("build_suite_release.bat")
        phase_script = read("tools/build_windows_release_phase.ps1")
        self.assertIn("environment: windows-release-signing", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("azure/login@532459ea530d8321f2fb9bb10d1e0bcf23869a43", workflow)
        self.assertIn("azure/artifact-signing-action@c7ab2a863ab5f9a846ddb8265964877ef296ee82", workflow)
        self.assertIn("AZURE_ARTIFACT_SIGNING_CERTIFICATE_PROFILE_NAME", workflow)
        self.assertIn("WINDOWS_SIGNING_CERTIFICATE_BASE64", workflow)
        self.assertIn("verify_windows_signatures.ps1", workflow)
        self.assertIn("WINDOWS_SIGNATURES_VERIFIED.json", workflow)
        self.assertIn("TimeStamperCertificate", read("tools/verify_windows_signatures.ps1"))
        self.assertIn("sign_windows_artifact.ps1", build_script)
        self.assertIn("Build Windows binaries for managed signing", workflow)
        self.assertIn(r"dist\FormatFoundry_Portable\FormatFoundry.exe", workflow)
        self.assertIn("-AdditionalPaths $portable", workflow)
        self.assertIn("FormatFoundry_Portable_${VERSION}_windows_x86_64.zip", workflow)
        self.assertLess(
            workflow.index("Sign app and updater with Azure Artifact Signing"),
            workflow.index("Build installer from signed binaries"),
        )
        self.assertLess(
            workflow.index("Build installer from signed binaries"),
            workflow.index("Sign installer with Azure Artifact Signing"),
        )
        for phase in ("Binaries", "Installer", "Stage"):
            self.assertIn(f'"{phase}"', phase_script)

    def test_signing_docs_reject_self_signed_public_releases(self) -> None:
        signing_guide = read("docs/WINDOWS_SIGNING.md")
        configure_script = read("tools/configure_windows_release_signing.ps1")
        self.assertIn("Do not generate a self-signed PFX", signing_guide)
        self.assertIn("Artifact Signing Certificate Profile Signer", signing_guide)
        self.assertIn("1.3.6.1.5.5.7.3.3", configure_script)
        self.assertIn('$_.name -eq "v*"', configure_script)
        self.assertNotIn("New-SelfSignedCertificate", configure_script)

    def test_debian_control_version_sorts_beta_before_future_stable(self) -> None:
        build_script = read("build_linux.sh")
        self.assertIn('DEBIAN_VERSION="${PACKAGE_VERSION/-beta/~beta}"', build_script)
        self.assertIn("Version: ${DEBIAN_VERSION}", build_script)
        self.assertIn('mktemp -d "${TMPDIR:-/tmp}/format-foundry-packaging.', build_script)
        self.assertIn('find "${DEB_ROOT}" -type d -exec chmod 755', build_script)
        self.assertIn("s/\\r$//", build_script)
        self.assertIn('APPDATA_OUTPUT_NAME="${DESKTOP_ID%.desktop}.appdata.xml"', build_script)
        self.assertIn('"${DEB_ROOT}/usr/share/doc/${PACKAGE_NAME}/copyright"', build_script)
        self.assertIn('"${APPDIR_ROOT}/usr/share/doc/${PACKAGE_NAME}/copyright"', build_script)

    def test_release_packages_include_local_license_terms(self) -> None:
        installer_source = read("installer/FormatFoundry.iss")
        windows_builder = read("tools/build_windows_release_phase.ps1")
        linux_builder = read("build_linux.sh")
        workflow = read(".github/workflows/cross-platform-build-release.yml")

        self.assertIn("LicenseFile=..\\LICENSE", installer_source)
        self.assertIn('Source: "..\\LICENSE"; DestDir: "{app}"', installer_source)
        self.assertIn('Join-Path $portableDirectory "LICENSE"', windows_builder)
        self.assertIn('cp -f "LICENSE" "$TAR_DIR/LICENSE"', linux_builder)
        self.assertIn("deb-smoke/usr/share/doc/format-foundry/copyright", workflow)

    def test_every_historical_changelog_release_is_labeled_alpha(self) -> None:
        changelog = read("CHANGELOG.md")
        headings = re.findall(r"^## \[([^\]]+)\] - (.+)$", changelog, flags=re.MULTILINE)
        self.assertGreater(len(headings), 1)
        for version, suffix in headings:
            if version == PACKAGE_VERSION:
                self.assertIn(DISPLAY_VERSION, suffix)
            else:
                self.assertIn("(Alpha)", suffix)

    def test_installer_routes_optional_tools_through_updater(self) -> None:
        installer_source = read("installer/FormatFoundry.iss")
        self.assertIn('Parameters: "--backends"', installer_source)
        self.assertIn("ReadRegisteredVersion", installer_source)
        self.assertIn("does not require Codex, Python", installer_source)

    def test_optional_idea_bank_is_bundled_but_disabled_by_default(self) -> None:
        app_source = read("modular_file_utility_suite.py")
        addon_source = read("addons/idea_bank.py")
        self.assertIn('"idea_bank_addon_enabled": False', app_source)
        self.assertIn("IdeaBankTab", app_source)
        self.assertIn('ADDON_ID = "idea-bank"', addon_source)

    def test_optional_pc_health_is_bundled_but_disabled_by_default(self) -> None:
        app_source = read("modular_file_utility_suite.py")
        addon_source = read("addons/pc_health.py")
        spec_source = read("FormatFoundry.spec")
        self.assertIn('"pc_health_addon_enabled": False', app_source)
        self.assertIn("PCHealthTab", app_source)
        self.assertIn('ADDON_ID = "pc-health-snapshot"', addon_source)
        self.assertIn("addons.pc_health", spec_source)

    def test_updater_has_no_developer_specific_git_path(self) -> None:
        updater_source = read("suite_updater.py")
        self.assertNotRegex(updater_source, r"[A-Za-z]:\\Users\\[^\\\n]+\\")
        self.assertIn('glob("app-*/resources/app/git/cmd/git.exe")', updater_source)

    def test_tagged_release_is_hash_bound_and_attested(self) -> None:
        workflow = read(".github/workflows/cross-platform-build-release.yml")
        self.assertIn("attestations: write", workflow)
        self.assertIn(
            "actions/attest@f7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6",
            workflow,
        )
        self.assertIn("tools/generate_provenance_manifest.py", workflow)
        self.assertIn("PROVENANCE.json", workflow)
        self.assertIn("github-attestation.json", workflow)
        self.assertLess(
            workflow.index("Generate GitHub release provenance attestation"),
            workflow.index("Publish coordinated release"),
        )

    def test_platform_builds_preserve_separate_checksum_manifests(self) -> None:
        windows_builder = read("tools/build_windows_release_phase.ps1")
        linux_builder = read("build_linux.sh")
        workflow = read(".github/workflows/cross-platform-build-release.yml")

        self.assertIn("SHA256SUMS-windows", windows_builder)
        self.assertIn("SHA256SUMS-linux", linux_builder)
        self.assertIn("release_bins/SHA256SUMS-windows", workflow)
        self.assertIn("release_bins/SHA256SUMS-linux", workflow)


if __name__ == "__main__":
    unittest.main()

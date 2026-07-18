import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "0.5.0-beta"
DISPLAY_VERSION = "Beta 0.5"
TRANSPORT_TAG = "v1.8.18"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8-sig")


class ReleaseContractTests(unittest.TestCase):
    def test_app_updater_and_installer_versions_match(self) -> None:
        app_source = read("modular_file_utility_suite.py")
        updater_source = read("suite_updater.py")
        installer_source = read("installer/FormatFoundry.iss")
        self.assertIn(f'APP_VERSION = "{PACKAGE_VERSION}"', app_source)
        self.assertIn(f'APP_VERSION_LABEL = "{DISPLAY_VERSION}"', app_source)
        self.assertIn(f'CURRENT_VERSION = "{PACKAGE_VERSION}"', updater_source)
        self.assertIn(f'CURRENT_VERSION_LABEL = "{DISPLAY_VERSION}"', updater_source)
        self.assertIn(f'#define MyAppVersion "{PACKAGE_VERSION}"', installer_source)
        self.assertIn(f'#define MyAppDisplayVersion "{DISPLAY_VERSION}"', installer_source)

    def test_public_install_assets_are_versioned_consistently(self) -> None:
        readme = read("README.md")
        expected_assets = (
            f"FormatFoundry_Setup_{PACKAGE_VERSION}.exe",
            f"format-foundry_{PACKAGE_VERSION}_amd64.deb",
            f"FormatFoundry_linux_{PACKAGE_VERSION}_x86_64.AppImage",
        )
        for asset in expected_assets:
            self.assertIn(asset, readme)
        self.assertIn("/releases/latest", readme)
        self.assertNotIn(f"/releases/download/v{PACKAGE_VERSION}/", readme)

    def test_alpha_to_beta_transport_contract_is_consistent(self) -> None:
        runtime = read("support_runtime.py")
        manifest = read("update_manifest.example.json")
        site = read("docs/site.js")
        workflow = read(".github/workflows/cross-platform-build-release.yml")
        self.assertIn(f'RELEASE_TRANSPORT_TAG = "{TRANSPORT_TAG}"', runtime)
        self.assertIn(f'"latest_version": "{TRANSPORT_TAG}"', manifest)
        self.assertIn(f'"release_tag": "{TRANSPORT_TAG}"', manifest)
        self.assertIn(f'const fallbackReleaseTag = "{TRANSPORT_TAG}"', site)
        self.assertIn("detectPackageVersion", site)
        self.assertIn("steps.prep.outputs.package_version", workflow)

    def test_tagged_windows_release_fails_closed_without_signatures(self) -> None:
        workflow = read(".github/workflows/cross-platform-build-release.yml")
        build_script = read("build_suite_release.bat")
        self.assertIn("WINDOWS_SIGNING_CERTIFICATE_BASE64", workflow)
        self.assertIn("verify_windows_signatures.ps1", workflow)
        self.assertIn("WINDOWS_SIGNATURES_VERIFIED.json", workflow)
        self.assertIn("sign_windows_artifact.ps1", build_script)

    def test_debian_control_version_sorts_beta_before_future_stable(self) -> None:
        build_script = read("build_linux.sh")
        self.assertIn('DEBIAN_VERSION="${PACKAGE_VERSION/-beta/~beta}"', build_script)
        self.assertIn("Version: ${DEBIAN_VERSION}", build_script)

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


if __name__ == "__main__":
    unittest.main()

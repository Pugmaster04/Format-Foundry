import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app_identity import DISPLAY_VERSION, MINIMUM_COMPATIBLE_VERSION, PACKAGE_VERSION
from suite_updater import UpdaterApp
from support_runtime import evaluate_manifest_compatibility, format_release_label, is_compatible_release, normalize_update_metadata


class SecurityReleasePolicyTests(unittest.TestCase):
    def test_every_alpha_and_pre_security_beta_is_incompatible(self):
        for version in ("v1.8.17", "Alpha 99.0.0", "99.0.0-alpha", "0.7.1-beta", "Beta 7.1.4", "Release Candidate 7.1.4"):
            with self.subTest(version=version):
                self.assertFalse(is_compatible_release(version))
                result = evaluate_manifest_compatibility({}, {"latest_version": version})
                self.assertFalse(result["allowed"])
                self.assertEqual(result["status"], "incompatible")

    def test_security_release_and_newer_supported_releases_are_compatible(self):
        for version in (PACKAGE_VERSION, DISPLAY_VERSION, "7.1.6-beta", "Release Candidate 7.1.6", "Stable 7.1.6"):
            with self.subTest(version=version):
                self.assertTrue(is_compatible_release(version))
                self.assertTrue(evaluate_manifest_compatibility({}, {"latest_version": version})["allowed"])

    def test_unknown_download_version_is_not_allowed(self):
        self.assertFalse(evaluate_manifest_compatibility({}, {"download_url": "https://example.test/setup.exe"})["allowed"])

    def test_current_package_cannot_override_an_incompatible_explicit_label(self):
        result = evaluate_manifest_compatibility({}, {"package_version": PACKAGE_VERSION, "release_label": "Alpha 1.8.17"})
        self.assertFalse(result["allowed"])

    def test_security_label_survives_transport_tag_and_display_formatting(self):
        manifest = normalize_update_metadata({"latest_version": "v1.8.18", "release_label": DISPLAY_VERSION, "package_version": PACKAGE_VERSION})
        self.assertEqual(format_release_label(manifest["latest_version"]), DISPLAY_VERSION)
        self.assertTrue(evaluate_manifest_compatibility({}, manifest)["allowed"])

    def test_incompatible_browser_download_is_blocked(self):
        updater = UpdaterApp.__new__(UpdaterApp)
        updater.last_compatibility = {"allowed": False, "status": "incompatible"}
        with patch("suite_updater.format_foundry_package", return_value=None), \
                patch("suite_updater.webbrowser.open") as opened, patch("suite_updater.messagebox.showwarning") as warning:
            updater._open_download_link()
        opened.assert_not_called()
        warning.assert_called_once()

    def test_release_policy_and_manifest_share_canonical_identity(self):
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / "docs/release-security.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "update_manifest.example.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["minimumCompatibleVersion"], MINIMUM_COMPATIBLE_VERSION)
        self.assertEqual(policy["minimumCompatibleLabel"], DISPLAY_VERSION)
        self.assertEqual(manifest["package_version"], PACKAGE_VERSION)
        self.assertEqual(manifest["release_label"], DISPLAY_VERSION)
        self.assertTrue(all(not release["compatible"] and not release["downloadsEnabled"] for release in policy["incompatibleReleases"]))

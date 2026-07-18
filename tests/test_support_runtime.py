import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support_runtime


class SupportRuntimeTests(unittest.TestCase):
    def test_beta_lifecycle_supersedes_every_unlabeled_alpha(self) -> None:
        self.assertTrue(support_runtime.is_release_newer("v0.5.0-beta", "1.8.17"))
        self.assertFalse(support_runtime.is_release_newer("1.8.17", "v0.5.0-beta"))
        self.assertEqual(support_runtime.format_release_label("v0.5.0-beta"), "Beta 0.5")
        self.assertTrue(support_runtime.is_release_newer("Release Candidate 0.6", "Beta 99.0"))
        self.assertFalse(support_runtime.is_release_newer("Beta 99.0", "Release Candidate 0.6"))
        self.assertEqual(support_runtime.format_release_label("Release Candidate 0.6"), "Release Candidate 0.6")

    def test_environment_snapshot_reuses_backend_details_override(self) -> None:
        cached = {"ffmpeg": {"detected": True, "path": "ffmpeg", "version": "7.1"}}
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch(
            "support_runtime.collect_backend_details",
            side_effect=AssertionError("backend probes should not run"),
        ):
            root = Path(temp_dir)
            result = support_runtime.build_environment_snapshot(
                app_title="Format Foundry",
                app_version="1.8.17",
                settings_dir=root,
                runtime_dir=root,
                script_dir=root,
                resource_dir=root,
                backend_paths={"ffmpeg": "ffmpeg"},
                backend_details_override=cached,
            )

        self.assertEqual(result["backends"], cached)

    def test_normalize_update_metadata_accepts_github_release_payload(self) -> None:
        result = support_runtime.normalize_update_metadata(
            {
                "tag_name": "v1.8.17",
                "html_url": "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.17",
                "body": "Release notes",
            }
        )

        self.assertEqual(result["latest_version"], "v1.8.17")
        self.assertEqual(result["release_url"], "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.17")
        self.assertEqual(result["notes"], "Release notes")

    def test_explicit_beta_release_name_overrides_legacy_transport_tag(self) -> None:
        result = support_runtime.normalize_update_metadata(
            {
                "tag_name": support_runtime.RELEASE_TRANSPORT_TAG,
                "name": "Format Foundry Beta 0.5",
                "html_url": "https://github.com/Pugmaster04/Format-Foundry/releases/tag/v1.8.18",
            }
        )

        self.assertEqual(result["latest_version"], "Format Foundry Beta 0.5")
        self.assertEqual(result["release_tag"], "v1.8.18")
        self.assertFalse(support_runtime.is_release_newer(result["latest_version"], "Beta 0.5"))

    def test_generic_release_name_keeps_numeric_tag_identity(self) -> None:
        result = support_runtime.normalize_update_metadata(
            {"tag_name": "v1.8.17", "name": "Format Foundry v1.8.17", "html_url": "https://example.test"}
        )

        self.assertEqual(result["latest_version"], "v1.8.17")

    def test_manifest_preserves_numeric_transport_for_alpha_clients(self) -> None:
        result = support_runtime.normalize_update_metadata(
            {"latest_version": "v1.8.18", "release_label": "Beta 0.5", "package_version": "0.5.0-beta"}
        )

        self.assertEqual(result["latest_version"], "Beta 0.5")
        self.assertEqual(result["transport_version"], "v1.8.18")

    def test_libreoffice_timeout_degrades_without_error(self) -> None:
        with mock.patch(
            "support_runtime.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["soffice", "--headless", "--version"],
                timeout=3,
            ),
        ):
            result = support_runtime._probe_backend_version("libreoffice", "C:/LibreOffice/program/soffice.exe")

        self.assertTrue(result["detected"])
        self.assertEqual(result["path"], "C:/LibreOffice/program/soffice.exe")
        self.assertEqual(result["version"], "")
        self.assertEqual(result["raw"], "")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["note"], "Version probe timed out; backend remains usable.")


if __name__ == "__main__":
    unittest.main()

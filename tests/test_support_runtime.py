import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support_runtime


class SupportRuntimeTests(unittest.TestCase):
    def test_home_paths_are_aliased_for_display_only(self) -> None:
        home = Path.home()
        private_path = home / "AppData" / "Local" / "Tool" / "tool.exe"
        self.assertEqual(
            support_runtime.display_path_with_home_alias(private_path),
            str(Path("~") / "AppData" / "Local" / "Tool" / "tool.exe"),
        )
        outside_path = Path(home.anchor) / "Program Files" / "Tool" / "tool.exe"
        self.assertEqual(support_runtime.display_path_with_home_alias(outside_path), str(outside_path))

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
        with mock.patch("support_runtime.current_platform_key", return_value="linux"), mock.patch(
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

    def test_windows_libreoffice_reads_metadata_without_launching(self) -> None:
        with (
            mock.patch("support_runtime.current_platform_key", return_value="windows"),
            mock.patch("support_runtime._windows_file_version", return_value="26.2.1.2"),
            mock.patch("support_runtime.subprocess.run") as run,
        ):
            result = support_runtime._probe_backend_version("libreoffice", r"C:\Program Files\LibreOffice\program\soffice.exe")

        run.assert_not_called()
        self.assertEqual(result["version"], "26.2.1.2")
        self.assertIn("Windows file metadata", result["raw"])

    def test_atomic_json_write_replaces_complete_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text('{"old": true}', encoding="utf-8")

            support_runtime.atomic_write_json(path, {"new": True, "count": 2})

            self.assertEqual(path.read_text(encoding="utf-8"), '{\n  "new": true,\n  "count": 2\n}\n')
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_backend_details_preserve_input_order_when_probed_in_parallel(self) -> None:
        paths = {"ffmpeg": "ffmpeg", "pandoc": "pandoc", "aria2": None}

        def fake_probe(key: str, path: str, _kwargs=None):
            return {"detected": True, "path": path, "version": key, "raw": "", "error": ""}

        with mock.patch("support_runtime._probe_backend_version", side_effect=fake_probe):
            details = support_runtime.collect_backend_details(paths)

        self.assertEqual(list(details), list(paths))
        self.assertEqual(details["ffmpeg"]["version"], "ffmpeg")
        self.assertFalse(details["aria2"]["detected"])

    def test_backend_version_cache_is_bounded_and_manual_refresh_bypasses_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            executable = root / "ffmpeg"
            executable.write_text("fixture", encoding="utf-8")
            cache_path = root / "backend_versions.json"
            result = {"detected": True, "path": str(executable), "version": "7.1", "raw": "", "error": ""}
            with mock.patch("support_runtime._probe_backend_version", return_value=dict(result)) as probe:
                first = support_runtime.collect_backend_details(
                    {"ffmpeg": str(executable)}, cache_path=cache_path, cache_limit=1
                )
                second = support_runtime.collect_backend_details(
                    {"ffmpeg": str(executable)}, cache_path=cache_path, cache_limit=1
                )
                refreshed = support_runtime.collect_backend_details(
                    {"ffmpeg": str(executable)}, cache_path=cache_path, force_refresh=True, cache_limit=1
                )

            self.assertEqual(probe.call_count, 2)
            self.assertFalse(first["ffmpeg"]["cache_hit"])
            self.assertTrue(second["ffmpeg"]["cache_hit"])
            self.assertFalse(refreshed["ffmpeg"]["cache_hit"])
            self.assertTrue(first["ffmpeg"]["detected_at_utc"].endswith("Z"))


if __name__ == "__main__":
    unittest.main()

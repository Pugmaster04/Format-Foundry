import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from accessibility_support import contrast_ratio, meets_wcag_aa, relative_luminance
from app_identity import DISPLAY_VERSION, PACKAGE_VERSION, PRODUCT_NAME
from job_ledger import ACTIVE_JOB_STATUSES, JobLedger
from optional_dependencies import optional_module
from settings_support import CURRENT_SETTINGS_SCHEMA_VERSION, SETTINGS_SCHEMA_KEY, load_settings_document


class IdentityAndAccessibilityTests(unittest.TestCase):
    def test_canonical_identity_is_consumer_facing(self) -> None:
        self.assertEqual(PRODUCT_NAME, "Format Foundry")
        self.assertEqual(PACKAGE_VERSION, "0.5.0-beta")
        self.assertEqual(DISPLAY_VERSION, "Beta 0.5")

    def test_contrast_helpers_match_wcag_reference_values(self) -> None:
        self.assertAlmostEqual(relative_luminance("#000"), 0.0)
        self.assertAlmostEqual(relative_luminance("#fff"), 1.0)
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21.0)
        self.assertTrue(meets_wcag_aa("#ffffff", "#17465a"))
        self.assertFalse(meets_wcag_aa("#777777", "#ffffff"))

    def test_every_shared_palette_text_pair_meets_wcag_aa(self) -> None:
        from modular_file_utility_suite import SuiteApp

        text_pairs = (
            ("title_fg", "card_bg"),
            ("subtitle_fg", "card_bg"),
            ("meta_fg", "window_bg"),
            ("muted_fg", "surface_bg"),
            ("button_fg", "button_bg"),
            ("input_fg", "input_bg"),
            ("tab_fg", "tab_bg"),
            ("status_fg", "status_bg"),
            ("log_fg", "log_bg"),
        )
        for dark_mode in (False, True):
            for high_contrast in (False, True):
                app = SuiteApp.__new__(SuiteApp)
                app.settings = {"high_contrast_mode": high_contrast}
                app._window_bar_color_override = None
                palette = app._theme_palette(dark_mode)
                for foreground, background in text_pairs:
                    with self.subTest(dark=dark_mode, high_contrast=high_contrast, pair=(foreground, background)):
                        self.assertTrue(meets_wcag_aa(palette[foreground], palette[background]))


class SettingsMigrationTests(unittest.TestCase):
    def test_legacy_settings_are_migrated_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "settings.json"
            path.write_text(json.dumps({"show_overview": True, "reduce_animations": True}), encoding="utf-8")
            result = load_settings_document(path, {"show_overview_panel": False, "reduce_motion": False})
            self.assertTrue(result.migrated)
            self.assertTrue(result.data["show_overview_panel"])
            self.assertTrue(result.data["reduce_motion"])
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved[SETTINGS_SCHEMA_KEY], CURRENT_SETTINGS_SCHEMA_VERSION)

    def test_corrupt_settings_preserve_recovery_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "settings.json"
            path.write_text("{not-json", encoding="utf-8")
            result = load_settings_document(path, {"dark_mode": False})
            self.assertIn("reset", result.notice)
            self.assertIsNotNone(result.recovery_path)
            self.assertEqual(result.recovery_path.read_text(encoding="utf-8"), "{not-json")

    def test_future_settings_are_loaded_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "settings.json"
            path.write_text(json.dumps({SETTINGS_SCHEMA_KEY: 99, "dark_mode": True}), encoding="utf-8")
            result = load_settings_document(path, {"dark_mode": False})
            self.assertTrue(result.read_only)
            self.assertTrue(result.data["dark_mode"])


class JobLedgerTests(unittest.TestCase):
    def test_jobs_persist_status_and_config_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            ledger = JobLedger(Path(temporary_directory) / "jobs.sqlite3")
            added = ledger.add(
                {
                    "module": "Convert",
                    "preset": "Web image",
                    "input": "input.tif",
                    "output": "output",
                    "config": {"target_format": "png"},
                }
            )
            ledger.update_status(added["job_id"], "running")
            self.assertEqual(JobLedger(ledger.database_path).recover_interrupted(), 1)
            restored = ledger.list(ACTIVE_JOB_STATUSES)
            self.assertEqual(restored[0]["status"], "interrupted")
            self.assertEqual(restored[0]["config"], {"target_format": "png"})

    def test_invalid_status_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            ledger = JobLedger(Path(temporary_directory) / "jobs.sqlite3")
            with self.assertRaises(ValueError):
                ledger.update_status("missing", "unknown")


class OptionalDependencyTests(unittest.TestCase):
    def tearDown(self) -> None:
        optional_module.cache_clear()

    def test_missing_optional_module_degrades_to_none(self) -> None:
        optional_module.cache_clear()
        with mock.patch("optional_dependencies.importlib.import_module", side_effect=ImportError("missing")):
            self.assertIsNone(optional_module("format_foundry_missing_test_module"))


if __name__ == "__main__":
    unittest.main()

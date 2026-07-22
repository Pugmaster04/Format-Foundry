import hashlib
import json
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from format_foundry_provenance import PROJECT_PROVENANCE_ID

ROOT = Path(__file__).resolve().parents[1]
MEDIA_ROOT = ROOT / "submission-media"


class SubmissionMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((MEDIA_ROOT / "MEDIA_MANIFEST.json").read_text(encoding="utf-8"))
        cls.catalog = json.loads((MEDIA_ROOT / "media-catalog.json").read_text(encoding="utf-8"))

    def test_manifest_hashes_dimensions_and_png_identity(self) -> None:
        self.assertEqual(self.manifest["identity"]["provenance_id"], PROJECT_PROVENANCE_ID)
        self.assertEqual(self.manifest["generated_at_utc"], self.catalog["generated_at_utc"])
        self.assertGreaterEqual(len(self.manifest["assets"]), 14)
        for item in self.manifest["assets"]:
            path = MEDIA_ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
            with Image.open(path) as image:
                self.assertEqual(image.size, (item["width"], item["height"]))
                self.assertEqual(image.info.get("Provenance-ID"), PROJECT_PROVENANCE_ID)

    def test_upload_ready_images_meet_declared_size_contract(self) -> None:
        upload_assets = [item for item in self.manifest["assets"] if item.get("upload_order") is not None]
        self.assertEqual([item["upload_order"] for item in upload_assets], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual((upload_assets[0]["width"], upload_assets[0]["height"]), (1200, 800))
        for item in upload_assets:
            self.assertLess(item["bytes"], 5 * 1024 * 1024, item["path"])

    def test_media_archive_is_current_and_contains_no_cache_files(self) -> None:
        archive_path = MEDIA_ROOT / "Format-Foundry-Devpost-Media-Kit.zip"
        checksum = (MEDIA_ROOT / f"{archive_path.name}.sha256").read_text(encoding="ascii").split()[0]
        self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(), checksum)
        with zipfile.ZipFile(archive_path) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
        self.assertIn("exports/gallery-05-idea-bank-1600x900.png", names)
        self.assertIn("exports/gallery-06-pc-health-1600x900.png", names)
        self.assertIn("screenshots/format-foundry-idea-bank-windows.png", names)
        self.assertIn("screenshots/format-foundry-pc-health-windows.png", names)
        self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))


if __name__ == "__main__":
    unittest.main()

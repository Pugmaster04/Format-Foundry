import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from addons.idea_bank import DATA_SCHEMA, IdeaBankError, IdeaBankStore


class IdeaBankStoreTests(unittest.TestCase):
    def test_create_update_search_and_reload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "ideas.json"
            store = IdeaBankStore(data_path)
            created = store.create(
                title="Build a guided conversion preset",
                description="Help new users choose safe defaults.",
                tags="UX, Conversion, ux",
            )
            updated = store.update(
                created.idea_id,
                title=created.title,
                description=created.description,
                tags=created.tags,
                status="Planned",
            )

            self.assertEqual(updated.status, "Planned")
            self.assertEqual(updated.tags, ("UX", "Conversion"))
            self.assertEqual([item.idea_id for item in store.search("safe defaults", "Planned")], [created.idea_id])

            reloaded = IdeaBankStore(data_path)
            self.assertEqual(reloaded.get(created.idea_id).status, "Planned")
            payload = json.loads(data_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], DATA_SCHEMA)

    def test_delete_and_csv_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = IdeaBankStore(root / "ideas.json")
            record = store.create(title="Portable add-on", tags="Architecture")
            csv_path = root / "ideas.csv"
            store.export_csv(csv_path)

            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][0:3], ["Title", "Status", "Tags"])
            self.assertEqual(rows[1][0], "Portable add-on")

            deleted = store.delete(record.idea_id)
            self.assertEqual(deleted.idea_id, record.idea_id)
            self.assertEqual(store.records, [])

    def test_malformed_data_fails_without_overwriting_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "ideas.json"
            original = "{not-json"
            data_path.write_text(original, encoding="utf-8")

            with self.assertRaises(IdeaBankError):
                IdeaBankStore(data_path)

            self.assertEqual(data_path.read_text(encoding="utf-8"), original)

    def test_oversized_create_and_update_roll_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "ideas.json"
            store = IdeaBankStore(data_path)
            with patch("addons.idea_bank.MAX_DATA_BYTES", 120):
                with self.assertRaises(IdeaBankError):
                    store.create(title="Too large", description="x" * 500)
            self.assertEqual(store.records, [])
            self.assertFalse(data_path.exists())

            original = store.create(title="Keep me")
            original_bytes = data_path.read_bytes()
            with patch("addons.idea_bank.MAX_DATA_BYTES", len(original_bytes) + 10):
                with self.assertRaises(IdeaBankError):
                    store.update(
                        original.idea_id,
                        title="Changed",
                        description="y" * 500,
                        tags=(),
                        status="Inbox",
                    )
            self.assertEqual(store.get(original.idea_id).title, "Keep me")
            self.assertEqual(data_path.read_bytes(), original_bytes)

    def test_csv_export_neutralizes_spreadsheet_formulas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = IdeaBankStore(root / "ideas.json")
            store.create(title="=WEBSERVICE(example)", description="+cmd", tags="@external")
            csv_path = root / "ideas.csv"
            store.export_csv(csv_path)

            with csv_path.open(newline="", encoding="utf-8") as handle:
                row = list(csv.reader(handle))[1]
            self.assertTrue(row[0].startswith("'="))
            self.assertTrue(row[2].startswith("'@"))
            self.assertTrue(row[3].startswith("'+"))


if __name__ == "__main__":
    unittest.main()

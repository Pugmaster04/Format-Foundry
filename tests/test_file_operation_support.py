import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from file_operation_support import apply_renames, commit_output, plan_renames


class SafeFilesTests(unittest.TestCase):
    def test_duplicate_planned_targets_are_reserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b, target = root / "a.txt", root / "b.txt", root / "merged.txt"
            a.write_text("first")
            b.write_text("second")
            rows = plan_renames([(a, target), (b, target)])
            self.assertEqual(apply_renames(rows), 2)
            self.assertEqual(target.read_text(), "first")
            self.assertEqual((root / "merged_1.txt").read_text(), "second")

    def test_changed_preview_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "a", root / "b"
            source.write_text("original")
            rows = plan_renames([(source, target)])
            target.write_text("new arrival")
            with self.assertRaises(FileExistsError):
                apply_renames(rows)
            self.assertEqual(source.read_text(), "original")
            self.assertEqual(target.read_text(), "new arrival")

    def test_link_failure_keeps_all_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "a"
            source.write_text("original")
            with patch("file_operation_support.os.link", side_effect=OSError("unsupported")):
                with self.assertRaises(OSError):
                    apply_renames([(source, root / "b")])
            self.assertEqual(source.read_text(), "original")

    def test_commit_does_not_overwrite_new_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "stage", root / "out"
            source.write_text("result")
            target.write_text("keep")
            with self.assertRaises(FileExistsError):
                commit_output(source, target, None)
            self.assertEqual(target.read_text(), "keep")

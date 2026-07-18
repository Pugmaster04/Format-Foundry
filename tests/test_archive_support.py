import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from archive_support import safe_extract_tar, safe_extract_zip


class ArchiveSupportTests(unittest.TestCase):
    def test_safe_extract_zip_extracts_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            archive_path = temp / "safe.zip"
            destination = temp / "output"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("folder/file.txt", "safe")

            safe_extract_zip(archive_path, destination)

            self.assertEqual((destination / "folder" / "file.txt").read_text(encoding="utf-8"), "safe")

    def test_safe_extract_zip_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            archive_path = temp / "unsafe.zip"
            destination = temp / "output"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../escaped.txt", "unsafe")

            with self.assertRaisesRegex(RuntimeError, "escapes the destination"):
                safe_extract_zip(archive_path, destination)

            self.assertFalse((temp / "escaped.txt").exists())

    def test_safe_extract_tar_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            archive_path = temp / "unsafe.tar"
            destination = temp / "output"
            payload = b"unsafe"
            with tarfile.open(archive_path, "w") as archive:
                member = tarfile.TarInfo("../escaped.txt")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))

            with self.assertRaisesRegex(RuntimeError, "escapes the destination"):
                safe_extract_tar(archive_path, destination)

            self.assertFalse((temp / "escaped.txt").exists())

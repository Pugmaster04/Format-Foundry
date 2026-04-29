import tempfile
import unittest
from pathlib import Path

from tools import verify_repo_integrity


class VerifyRepoIntegrityTests(unittest.TestCase):
    def test_missing_root_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative_path in verify_repo_integrity.REQUIRED_ROOT_FILES:
                if relative_path == "suite_updater.py":
                    continue
                (root / relative_path).write_text("placeholder", encoding="utf-8")

            missing = verify_repo_integrity.find_missing_required_files(root)

            self.assertEqual(missing, ["suite_updater.py"])

    def test_all_files_present_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative_path in verify_repo_integrity.REQUIRED_ROOT_FILES:
                (root / relative_path).write_text("placeholder", encoding="utf-8")

            missing = verify_repo_integrity.find_missing_required_files(root)

            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()

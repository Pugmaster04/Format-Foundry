import subprocess
import unittest
from unittest import mock

import support_runtime


class SupportRuntimeTests(unittest.TestCase):
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

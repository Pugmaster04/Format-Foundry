import subprocess
import unittest
from unittest.mock import patch

from addons import pc_health


class PCHealthTests(unittest.TestCase):
    def test_format_bytes_handles_missing_and_large_values(self) -> None:
        self.assertEqual(pc_health.format_bytes(None), "Unavailable")
        self.assertEqual(pc_health.format_bytes(1024), "1.0 KiB")
        self.assertEqual(pc_health.format_bytes(5 * 1024**3), "5.0 GiB")

    def test_legacy_powershell_timestamp_is_human_readable(self) -> None:
        self.assertEqual(pc_health._format_security_timestamp("/Date(1784371709000)/"), "2026-07-18 10:48 UTC")

    def test_non_windows_security_status_is_explicitly_limited(self) -> None:
        with patch.object(pc_health.os, "name", "posix"):
            status, detail = pc_health._security_snapshot()

        self.assertEqual(status, "Platform managed")
        self.assertIn("distribution security center", detail)

    def test_windows_defender_status_uses_bounded_read_only_query(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout=(
                '{"AMServiceEnabled":true,"AntivirusEnabled":true,'
                '"RealTimeProtectionEnabled":true,"AntivirusSignatureLastUpdated":"2026-07-18"}'
            ),
            stderr="",
        )
        with (
            patch.object(pc_health.os, "name", "nt"),
            patch.object(pc_health.shutil, "which", return_value="powershell"),
            patch.object(pc_health.subprocess, "run", return_value=completed) as run,
        ):
            status, detail = pc_health._security_snapshot()

        self.assertEqual(status, "Protection active")
        self.assertIn("2026-07-18", detail)
        self.assertEqual(run.call_args.kwargs["timeout"], pc_health.SECURITY_TIMEOUT_SECONDS)
        self.assertFalse(run.call_args.kwargs["check"])

    def test_collect_snapshot_omits_machine_name_and_uses_bounded_fields(self) -> None:
        disk = type("Disk", (), {"total": 1000, "free": 400})()
        with (
            patch.object(pc_health, "_memory_snapshot", return_value=(800, 300)),
            patch.object(pc_health, "_security_snapshot", return_value=("Active", "Read-only")),
            patch.object(pc_health.shutil, "disk_usage", return_value=disk),
            patch.object(pc_health.platform, "system", return_value="TestOS"),
            patch.object(pc_health.platform, "release", return_value="1"),
            patch.object(pc_health.platform, "machine", return_value="x86_64"),
        ):
            snapshot = pc_health.collect_snapshot()

        self.assertEqual(snapshot.operating_system, "TestOS")
        self.assertEqual(snapshot.memory_available_bytes, 300)
        self.assertEqual(snapshot.home_disk_free_bytes, 400)
        self.assertNotIn("host", snapshot.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()

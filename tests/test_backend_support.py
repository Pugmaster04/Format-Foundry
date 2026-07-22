import tempfile
import unittest
from pathlib import Path
from unittest import mock

import backend_support


class BackendSupportTests(unittest.TestCase):
    @mock.patch("backend_support.current_platform_key", return_value="linux")
    @mock.patch("backend_support.shutil.which", return_value="/mnt/c/Tools/backend.exe")
    def test_native_which_rejects_windows_binary_on_linux(self, _which: mock.Mock, _platform: mock.Mock) -> None:
        self.assertIsNone(backend_support._native_which("backend"))

    @mock.patch("backend_support.current_platform_key", return_value="windows")
    @mock.patch("backend_support.shutil.which", return_value=r"C:\Tools\backend.exe")
    def test_native_which_accepts_windows_binary_on_windows(self, _which: mock.Mock, _platform: mock.Mock) -> None:
        self.assertEqual(backend_support._native_which("backend"), r"C:\Tools\backend.exe")

    def test_backend_contract_has_unique_names_keys_and_https_links(self) -> None:
        names = [definition.name for definition in backend_support.BACKEND_DEFINITIONS]
        keys = [definition.key for definition in backend_support.BACKEND_DEFINITIONS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(keys), len(set(keys)))
        for definition in backend_support.BACKEND_DEFINITIONS:
            self.assertTrue(definition.homepage.startswith("https://"))
            self.assertTrue(definition.docs.startswith("https://"))
            self.assertTrue(definition.download.startswith("https://"))
            self.assertTrue(definition.enables)

    def test_windows_install_args_are_fixed_and_non_shell(self) -> None:
        args, reason = backend_support.backend_install_process_args(
            "FFmpeg",
            platform_key="windows",
            executable_override=r"C:\Windows\winget.exe",
        )
        self.assertEqual(reason, "")
        self.assertEqual(args[0], r"C:\Windows\winget.exe")
        self.assertIn("Gyan.FFmpeg", args)
        self.assertIn("--disable-interactivity", args)

    def test_linux_install_args_use_graphical_privilege_helper(self) -> None:
        args, reason = backend_support.backend_install_process_args(
            "Aria2",
            platform_key="linux",
            package_manager="apt",
            executable_override="/usr/bin/apt-get",
            privilege_helper_override="/usr/bin/pkexec",
        )
        self.assertEqual(reason, "")
        self.assertEqual(args, ["/usr/bin/pkexec", "/usr/bin/apt-get", "install", "-y", "aria2"])

    def test_ffmpeg_and_ffprobe_install_only_once(self) -> None:
        targets = backend_support.unique_install_targets(["FFmpeg", "FFprobe", "Aria2"])
        self.assertEqual(targets, ["FFmpeg", "Aria2"])

    @mock.patch("backend_support.shutil.which", return_value=None)
    def test_missing_winget_has_consumer_facing_fallback(self, _which: mock.Mock) -> None:
        args, reason = backend_support.backend_install_process_args("Pandoc", platform_key="windows")
        self.assertEqual(args, [])
        self.assertIn("official download link", reason)

    @mock.patch("backend_support.shutil.which", return_value=None)
    def test_runtime_search_root_finds_packaged_aria2(self, _which: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            aria2_path = root / "aria2" / "aria2c.exe"
            aria2_path.parent.mkdir()
            aria2_path.write_bytes(b"test executable placeholder")

            real_existing = backend_support._existing

            def isolated_existing(candidate: object) -> str | None:
                if candidate is None:
                    return None
                path = Path(candidate)
                if root not in path.parents and path != root:
                    return None
                return real_existing(candidate)

            with mock.patch("backend_support._existing", side_effect=isolated_existing):
                paths = backend_support.detect_backend_paths(runtime_search_roots=[root])

        self.assertEqual(paths["aria2"], str(aria2_path))


if __name__ == "__main__":
    unittest.main()

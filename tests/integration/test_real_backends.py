from __future__ import annotations

import functools
import http.server
import os
import secrets
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace

from aria2_support import CompletionMonitor, build_download_command, reap_process
from backend_support import detect_backend_paths
from modular_file_utility_suite import TaskEngine

ENABLED = os.environ.get("FORMAT_FOUNDRY_REAL_BACKENDS", "").strip() == "1"


@unittest.skipUnless(ENABLED, "Set FORMAT_FOUNDRY_REAL_BACKENDS=1 to exercise installed backends.")
class RealBackendIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.backends = detect_backend_paths()

    def backend(self, key: str) -> str:
        value = str(self.backends.get(key) or "").strip()
        self.assertTrue(value, f"Required integration backend was not detected: {key}")
        return value

    def run_backend(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        timeout: float = 90.0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"Backend command failed: {command}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        return completed

    def test_ffmpeg_and_ffprobe_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "fixture.mp4"
            self.run_backend(
                [
                    self.backend("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=teal:s=32x32:d=0.25",
                    "-pix_fmt",
                    "yuv420p",
                    "-y",
                    str(output),
                ]
            )
            probe = self.run_backend(
                [self.backend("ffprobe"), "-v", "error", "-show_entries", "format=format_name", "-of", "default=nw=1", str(output)]
            )
            self.assertTrue(output.is_file())
            self.assertIn("mp4", probe.stdout)

    def test_app_webm_conversion_uses_compatible_codecs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture.mp4"
            self.run_backend([self.backend("ffmpeg"), "-f", "lavfi", "-i", "color=c=teal:s=32x32:d=0.25", "-y", str(source)])
            app = SimpleNamespace(backends=SimpleNamespace(ffmpeg=self.backend("ffmpeg")), settings={},
                                  resolve_output_path=lambda path, **_: path, run_process=self.run_backend)
            output = TaskEngine(app).convert_file(source, root, "webm", {})
            probe = self.run_backend([self.backend("ffprobe"), "-v", "error", "-show_entries", "stream=codec_name", str(output)])
            self.assertIn("vp9", probe.stdout)

    def test_app_aria2_rpc_download_completes_and_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.txt").write_text("Format Foundry download fixture", encoding="utf-8")
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                rpc_port = sock.getsockname()[1]
            token = secrets.token_urlsafe(32)
            command = build_download_command(self.backend("aria2"), root / "download", rpc_port,
                                             [f"http://127.0.0.1:{server.server_port}/fixture.txt"], secret=token)
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            try:
                monitor = CompletionMonitor(rpc_port, token)
                complete = False
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    try:
                        complete = monitor.complete()
                    except urllib.error.URLError:
                        pass
                    if complete:
                        break
                    time.sleep(0.5)
                self.assertTrue(complete, "Owned aria2 session did not complete")
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertEqual((root / "download/fixture.txt").read_bytes(), (root / "fixture.txt").read_bytes())
            finally:
                reap_process(process)
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_pandoc_converts_markdown_to_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "fixture.md"
            output = root / "fixture.html"
            source.write_text("# Format Foundry\n\nBackend integration.\n", encoding="utf-8")
            self.run_backend([self.backend("pandoc"), str(source), "-o", str(output)])
            self.assertIn("Format Foundry", output.read_text(encoding="utf-8"))

    def test_libreoffice_headless_exports_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "fixture.html"
            output_dir = root / "output"
            profile = root / "libreoffice-profile"
            output_dir.mkdir()
            source.write_text("<html><body><h1>Format Foundry</h1></body></html>", encoding="utf-8")
            profile_uri = profile.resolve().as_uri()
            self.run_backend(
                [
                    self.backend("libreoffice"),
                    "--headless",
                    f"-env:UserInstallation={profile_uri}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(source),
                ],
                timeout=120.0,
            )
            self.assertGreater((output_dir / "fixture.pdf").stat().st_size, 0)

    def test_sevenzip_archives_and_extracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "fixture.txt"
            archive = root / "fixture.7z"
            output = root / "extracted"
            source.write_text("Format Foundry archive fixture", encoding="utf-8")
            self.run_backend([self.backend("sevenzip"), "a", "-y", str(archive), source.name], cwd=root)
            self.run_backend([self.backend("sevenzip"), "x", "-y", f"-o{output}", str(archive)], cwd=root)
            self.assertEqual((output / source.name).read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))

    def test_imagemagick_creates_and_identifies_png(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "fixture.png"
            image_tool = self.backend("imagemagick")
            prefix = [image_tool] if Path(image_tool).stem.lower() != "magick" else [image_tool]
            self.run_backend(prefix + ["-size", "24x24", "xc:#117D8E", str(output)])
            self.assertGreater(output.stat().st_size, 0)

    def test_aria2_downloads_from_local_http_server(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            served = root / "served"
            downloaded = root / "downloaded"
            served.mkdir()
            downloaded.mkdir()
            payload = b"Format Foundry aria2 integration fixture\n" * 32
            (served / "fixture.bin").write_bytes(payload)
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(served))
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/fixture.bin"
                self.run_backend(
                    [
                        self.backend("aria2"),
                        "--allow-overwrite=true",
                        "--auto-file-renaming=false",
                        f"--dir={downloaded}",
                        "--out=fixture.bin",
                        url,
                    ]
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5.0)
            self.assertEqual((downloaded / "fixture.bin").read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()

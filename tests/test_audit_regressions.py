import hashlib
import io
import json
import queue
import tempfile
import unittest
import urllib.request
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from archive_support import create_archive, safe_extract_zip
from aria2_support import CompletionMonitor, call_rpc
from checksum_support import verify_checksums
from modular_file_utility_suite import ImagesTab, OperationCanceledError, SuiteApp, TaskEngine
from suite_updater import UpdaterApp
from support_runtime import evaluate_manifest_compatibility, evaluate_runtime_support
from update_security import PolicyRedirectHandler, download_verified, validate_url


class Response(io.BytesIO):
    def __init__(self, content, length=None):
        super().__init__(content)
        self.headers = {"Content-Length": str(len(content) if length is None else length)}


class AuditRegressions(unittest.TestCase):
    def test_newer_os_is_not_claimed_as_validated(self):
        report = evaluate_runtime_support({"os": {"platform_key": "linux", "architecture": "x86_64", "distribution_id": "ubuntu", "distribution_version": "26.04"}})
        self.assertEqual(report["status"], "best_effort")

    def test_unknown_backend_version_fails_declared_minimum(self):
        report = evaluate_manifest_compatibility({"os": {}, "backends": {"ffmpeg": {"detected": True, "version": ""}}},
                                                {"compatibility": {"minimum_backends": {"ffmpeg": "6.0"}}})
        self.assertFalse(report["allowed"])

    def test_failed_and_cancelled_images_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            for error in (ValueError("unsupported image"), OperationCanceledError("stopped")):
                tab = ImagesTab.__new__(ImagesTab)
                source = Path(directory) / "input.png"
                tab.files = [source]
                tab.output_dir = Mock(get=lambda: directory)
                tab.export_preset = lambda: {}
                tab.check_cancelled = lambda: None
                tab.status_var = Mock()
                tab.progress = Mock()
                tab.progress_percent_var = Mock()
                tab.log = Mock()
                tab.listbox = Mock()
                tab.remove_path_from_queue = Mock()
                tab.run_async = lambda work, **_: work()
                tab.app = SimpleNamespace(call_ui=lambda callback: callback(), engine=SimpleNamespace(process_image_file=Mock(side_effect=error)))
                with self.assertRaises(RuntimeError):
                    tab.run_images()
                tab.remove_path_from_queue.assert_not_called()
                self.assertEqual(tab.files, [source])

    def test_download_failures_preserve_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "setup.exe"
            target.write_bytes(b"keep")
            for opener in (Mock(side_effect=OSError("offline")), lambda *a, **k: Response(b"corrupt"), lambda *a, **k: Response(b"short", 100)):
                with self.assertRaises((OSError, ValueError)):
                    download_verified(urllib.request.Request("https://example.com/setup"), target, "a" * 64, opener=opener)
                self.assertEqual(target.read_bytes(), b"keep")
                self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_verified_download_replaces_only_after_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "setup"
            target.write_bytes(b"old")
            content = b"verified"
            download_verified(urllib.request.Request("https://example.com/setup"), target, hashlib.sha256(content).hexdigest(),
                              opener=lambda *a, **k: Response(content))
            self.assertEqual(target.read_bytes(), content)

    def test_redirect_policy_rejects_downgrade_and_foreign_host(self):
        handler = PolicyRedirectHandler(lambda url: validate_url(url, require_https=True, trusted_hosts=("github.com",)))
        for target in ("http://github.com/x", "https://untrusted.invalid/x", "https://user:pass@github.com/x"):
            with self.assertRaises(ValueError):
                handler.redirect_request(urllib.request.Request("https://github.com/x"), None, 302, "Found", {}, target)

    def test_ui_pump_continues_after_failure_and_reschedules(self):
        app = SuiteApp.__new__(SuiteApp)
        app.root = Mock()
        app.ui_queue = queue.Queue()
        app._append_logs = Mock()
        callback = Mock()
        app.ui_queue.put(("call", Mock(side_effect=ValueError("fixture"))))
        app.ui_queue.put(("call", callback))
        app._poll_ui_queue()
        callback.assert_called_once()
        app.root.after.assert_called_once()

    def test_office_writes_only_in_private_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, old, selected = root / "report.doc", root / "report.pdf", root / "report_1.pdf"
            source.write_text("source")
            old.write_bytes(b"preserve")
            commands = []

            def run(command):
                commands.append(command)
                destination = Path(command[command.index("--outdir") + 1])
                (destination / "report.pdf").write_bytes(b"converted")

            app = SimpleNamespace(backends=SimpleNamespace(pandoc="pandoc", libreoffice="soffice"),
                                  resolve_output_path=lambda *a, **k: selected, run_process=run)
            result = TaskEngine(app).convert_document(source, root, "pdf")
            self.assertEqual(result, selected)
            self.assertEqual(old.read_bytes(), b"preserve")
            self.assertEqual(selected.read_bytes(), b"converted")
            self.assertEqual(commands[0][0], "soffice")

    def test_wrong_platform_and_architecture_have_no_asset(self):
        app = UpdaterApp.__new__(UpdaterApp)
        assets = [{"name": "FormatFoundry_Setup_0.7.1-beta.exe", "browser_download_url": "https://github.com/setup.exe"},
                  {"name": "format-foundry_0.7.1-beta_amd64.deb", "browser_download_url": "https://github.com/setup.deb"}]
        with patch("suite_updater.current_platform_key", return_value="linux"), patch("suite_updater.current_arch_markers", return_value=("arm64",)), patch("suite_updater.is_debian_like_linux", return_value=True):
            self.assertEqual(app._select_release_asset(assets), (None, "", ""))

    def test_compatibility_denial_prevents_download(self):
        app = UpdaterApp.__new__(UpdaterApp)
        app.downloading = False
        app.last_compatibility = {"allowed": False}
        with patch("suite_updater.messagebox.showwarning") as warning:
            app._download_update_clicked()
        warning.assert_called_once()

    def test_rpc_errors_are_not_pause_success(self):
        for payload in ({"jsonrpc": "2.0", "id": "uch", "error": {"code": 1}}, {"jsonrpc": "2.0", "id": "wrong", "result": "OK"}):
            with self.assertRaises(RuntimeError):
                call_rpc(1, "pauseAll", opener=lambda *a, value=payload, **k: Response(json.dumps(value).encode()))

    def test_rpc_completion_waits_for_metadata_children(self):
        monitor = CompletionMonitor(1, "secret")
        stopped = [{"gid": "metadata", "status": "complete", "followedBy": ["child"]}]
        with patch("aria2_support.call_rpc", side_effect=lambda _port, method, *a, **k: stopped if method == "tellStopped" else []) as rpc:
            for _ in range(4):
                self.assertFalse(monitor.complete())
            stopped.append({"gid": "child", "status": "complete"})
            self.assertFalse(monitor.complete())
            self.assertFalse(monitor.complete())
            self.assertTrue(monitor.complete())
            self.assertEqual(rpc.call_args.args[1], "shutdown")

    def test_checksums_reject_empty_and_parse_relative_binary_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "checksums.txt"
            for content in ("", "garbage", "00  file.txt"):
                report.write_text(content)
                with self.assertRaises(ValueError):
                    verify_checksums(report, "sha256")
            (root / "file.txt").write_bytes(b"ok")
            report.write_text(hashlib.sha256(b"ok").hexdigest() + " *file.txt\n")
            self.assertEqual(verify_checksums(report, "sha256"), (1, []))

    def test_archives_exclude_output_and_preserve_existing_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "file.txt").write_text("original")
            archive = source / "result.zip"
            create_archive([source], archive, "zip")
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(bundle.namelist(), ["source/file.txt"])
            destination = root / "extracted"
            safe_extract_zip(archive, destination)
            extracted = destination / "source/file.txt"
            extracted.write_text("edited")
            with self.assertRaises(FileExistsError):
                safe_extract_zip(archive, destination)
            self.assertEqual(extracted.read_text(), "edited")

    def test_cancelled_archive_does_not_leave_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "file"
            source.write_bytes(b"a" * 3_000_000)
            calls = 0

            def cancel():
                nonlocal calls
                calls += 1
                if calls > 4:
                    raise InterruptedError("cancel")

            with self.assertRaises(InterruptedError):
                create_archive([source], root / "output.zip", "zip", cancel)
            self.assertFalse((root / "output.zip").exists())

    def test_streaming_zip_keeps_selected_compression_level(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data"
            source.write_bytes(b"repeated data " * 10000)
            create_archive([source], root / "plain.zip", "zip", level=0)
            create_archive([source], root / "compressed.zip", "zip", level=9)
            self.assertGreater((root / "plain.zip").stat().st_size, (root / "compressed.zip").stat().st_size * 10)

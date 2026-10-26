import ast
import http.server
import json
import os
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from archive_support import _safe_member_target, create_archive
from aria2_support import call_rpc
from code_translation import TranslationError, find_typescript_compiler, translate_project
from modular_file_utility_suite import OperationCanceledError, PresetsBatchTab, TaskEngine
from settings_support import load_settings_document
from suite_updater import UpdaterApp


class LocalRpcAuditTests(unittest.TestCase):
    def test_local_rpc_token_cannot_be_sent_through_configured_proxy(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.server.server_port, body))
                payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": self.server.server_port}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        direct = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (direct, proxy)]
        for thread in threads:
            thread.start()
        try:
            with patch("urllib.request.getproxies", return_value={"http": f"http://127.0.0.1:{proxy.server_port}"}), \
                    patch("urllib.request.proxy_bypass", return_value=False), patch("urllib.request._opener", None):
                result = call_rpc(direct.server_port, "tellActive", secret="owned-rpc-fixture", timeout=3)
            self.assertEqual(result, direct.server_port)
            self.assertEqual([port for port, _ in requests], [direct.server_port])
        finally:
            for server in (direct, proxy):
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join(timeout=3)


class OutputPreservationTests(unittest.TestCase):
    def test_failed_pillow_workflows_preserve_existing_output(self):
        for workflow in ("convert", "images", "compress"):
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, target = root / "source.png", root / "output.png"
                Image.new("RGB", (4, 4), "red").save(source)
                original = source.read_bytes()
                target.write_bytes(b"existing output")
                app = SimpleNamespace(
                    backends=SimpleNamespace(imagemagick=None), settings={},
                    resolve_output_path=lambda *args, target=target, **kwargs: target,
                    check_current_task_cancelled=lambda: None,
                )
                engine = TaskEngine(app)

                def fail_save(_image, path, **kwargs):
                    Path(path).write_bytes(b"partial output")
                    raise OSError("fixture encoder failure")

                with patch.object(Image.Image, "save", fail_save), self.assertRaisesRegex(OSError, "encoder failure"):
                    if workflow == "convert":
                        engine.convert_file(source, root, "png", {})
                    elif workflow == "images":
                        engine.process_image_file(source, root, {"target_format": "png"})
                    else:
                        engine.compress_file(source, root, "image_quality", {})
                self.assertEqual(target.read_bytes(), b"existing output")
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(list(root.glob(".foundry-output-*")), [])

    def test_failed_media_output_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source.mp4", root / "output.webm"
            source.write_bytes(b"source fixture")
            target.write_bytes(b"existing output")

            def fail_process(command):
                Path(command[-1]).write_bytes(b"partial output")
                raise RuntimeError("fixture backend failure")

            app = SimpleNamespace(
                backends=SimpleNamespace(ffmpeg="fixture-ffmpeg"), settings={}, run_process=fail_process,
                resolve_output_path=lambda *args, **kwargs: target, check_current_task_cancelled=lambda: None,
            )
            with self.assertRaisesRegex(RuntimeError, "backend failure"):
                TaskEngine(app).convert_file(source, root, "webm", {})
            self.assertEqual(target.read_bytes(), b"existing output")
            self.assertEqual(list(root.glob(".foundry-output-*")), [])

    def test_cancelled_media_output_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "output.webm"
            target.write_bytes(b"existing output")
            cancelled = False

            def run(command):
                nonlocal cancelled
                Path(command[-1]).write_bytes(b"finished fixture")
                cancelled = True

            def check():
                if cancelled:
                    raise OperationCanceledError("fixture cancellation")

            app = SimpleNamespace(
                backends=SimpleNamespace(ffmpeg="fixture-ffmpeg"), settings={}, run_process=run,
                resolve_output_path=lambda *args, **kwargs: target, check_current_task_cancelled=check,
            )
            with self.assertRaises(OperationCanceledError):
                TaskEngine(app).convert_file(root / "source.mp4", root, "webm", {})
            self.assertEqual(target.read_bytes(), b"existing output")

    def test_frame_extraction_uses_new_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / "source_frames"
            previous.mkdir()
            frame = previous / "frame_00001.png"
            frame.write_bytes(b"existing frame")

            def run(command):
                Path(command[-1].replace("%05d", "00001")).write_bytes(b"new frame")

            app = SimpleNamespace(backends=SimpleNamespace(ffmpeg="fixture-ffmpeg"), settings={},
                                  run_process=run, check_current_task_cancelled=lambda: None)
            output = TaskEngine(app).extract_from_media(root / "source.mp4", root, "frames_from_video", {})
            self.assertNotEqual(output, previous)
            self.assertEqual(frame.read_bytes(), b"existing frame")
            self.assertEqual((output / "frame_00001.png").read_bytes(), b"new frame")


class SettingsRecoveryAuditTests(unittest.TestCase):
    def test_failed_recovery_disables_writes_to_corrupt_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_bytes(b"corrupt original")
            with patch("settings_support._recovery_copy", return_value=None):
                result = load_settings_document(path, {})
            self.assertTrue(result.read_only)
            self.assertEqual(path.read_bytes(), b"corrupt original")

    def test_infinite_schema_version_cannot_crash_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"settings_schema_version":Infinity}', encoding="utf-8")
            result = load_settings_document(path, {"dark_mode": True})
            self.assertTrue(result.data["dark_mode"])

    def test_read_only_settings_migrate_in_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"borderless":true}', encoding="utf-8")
            original = path.read_bytes()
            with patch("settings_support.atomic_write_json", side_effect=PermissionError("fixture read-only settings")):
                result = load_settings_document(path, {"borderless_maximized": False})
            self.assertTrue(result.data["borderless_maximized"])
            self.assertTrue(result.read_only)
            self.assertEqual(path.read_bytes(), original)

    def test_repeated_recovery_preserves_both_original_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            fixed_time = Mock()
            fixed_time.strftime.return_value = "20261026T120000Z"
            with patch("settings_support.datetime") as clock:
                clock.now.return_value = fixed_time
                path.write_bytes(b"first invalid document")
                first = load_settings_document(path, {}).recovery_path
                path.write_bytes(b"second invalid document")
                second = load_settings_document(path, {}).recovery_path
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"first invalid document")
            self.assertEqual(second.read_bytes(), b"second invalid document")


class ArchiveAuditTests(unittest.TestCase):
    def test_missing_archive_input_does_not_replace_existing_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "output.zip"
            target.write_bytes(b"existing archive")
            with self.assertRaises((ValueError, FileNotFoundError)):
                create_archive([root / "missing"], target, "zip")
            self.assertEqual(target.read_bytes(), b"existing archive")

    def test_empty_directories_survive_archive_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            (source / "empty").mkdir(parents=True)
            output = create_archive([source], root / "output.zip", "zip")
            with zipfile.ZipFile(output) as archive:
                self.assertIn("source/empty/", archive.namelist())

    @unittest.skipUnless(os.name == "nt", "Windows archive namespace")
    def test_windows_device_and_alias_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("NUL", "NUL.txt", "COM1", "folder./file.txt", "folder /file.txt"):
                with self.subTest(name=name), self.assertRaises((ValueError, RuntimeError)):
                    _safe_member_target(Path(directory), name)


class FrozenBackendAuditTests(unittest.TestCase):
    def test_freezer_specs_exclude_outdated_ffmpeg_wheel(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("FormatFoundry.spec", "FormatFoundry_Portable.spec", "FormatFoundry_MSIX.spec"):
            with self.subTest(spec=name):
                tree = ast.parse((root / name).read_text(encoding="utf-8"))
                analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                                and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
                excluded = next(ast.literal_eval(keyword.value) for keyword in analysis.keywords if keyword.arg == "excludes")
                self.assertIn("imageio_ffmpeg", excluded)


class ManifestAndQueueAuditTests(unittest.TestCase):
    def test_updater_accepts_utf8_bom_and_rejects_non_object_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            app = UpdaterApp.__new__(UpdaterApp)
            path.write_text('{"latest_version":"2.0.0"}', encoding="utf-8-sig")
            self.assertEqual(app._read_manifest(str(path))["latest_version"], "2.0.0")
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                app._read_manifest(str(path))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO")
    def test_local_manifest_rejects_fifo_without_opening_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            os.mkfifo(path)
            with self.assertRaisesRegex(ValueError, "regular file"):
                UpdaterApp.__new__(UpdaterApp)._read_manifest(str(path))

    def test_malformed_presets_do_not_crash_or_overwrite_original(self):
        with tempfile.TemporaryDirectory() as directory:
            tab = PresetsBatchTab.__new__(PresetsBatchTab)
            tab.preset_file = Path(directory) / "presets.json"
            tab.preset_file.write_text(json.dumps({
                "broken": None, "wrong-config": {"module": "Convert", "config": []},
                "valid": {"module": "Convert", "config": {"target_format": "png"}},
            }), encoding="utf-8")
            original = tab.preset_file.read_bytes()
            tab.presets = {}
            tab.status_var = Mock()
            tab._load_presets()
            self.assertEqual(set(tab.presets), {"valid"})
            with patch("modular_file_utility_suite.messagebox.showerror"):
                self.assertFalse(tab._save_presets())
            self.assertEqual(tab.preset_file.read_bytes(), original)

    def test_bad_batch_output_does_not_abort_later_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad_output = root / "existing-file"
            bad_output.write_bytes(b"preserve")
            tab = PresetsBatchTab.__new__(PresetsBatchTab)
            tab.jobs = [
                {"job_id": "bad", "module": "Convert", "input": "first.png", "output": str(bad_output), "config": {}},
                {"job_id": "good", "module": "Convert", "input": "second.png", "output": str(root / "output"), "config": {}},
            ]
            tab.status_var = Mock()
            tab.check_cancelled = lambda: None
            tab.run_async_managed = lambda action, **kwargs: action()
            tab._set_job_status = lambda job, status, error="": job.update(status=status)
            tab.app = SimpleNamespace(engine=Mock(), call_ui=lambda action: action())
            with self.assertRaisesRegex(RuntimeError, "1 job.*failed"):
                tab.run_queue()
            self.assertEqual([job["status"] for job in tab.jobs], ["failed", "completed"])
            tab.app.engine.convert_file.assert_called_once()
            self.assertEqual(bad_output.read_bytes(), b"preserve")

    def test_metadata_probe_timeout_is_reported_without_hanging(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.mp4"
            source.write_bytes(b"owned metadata fixture")
            app = SimpleNamespace(backends=SimpleNamespace(ffprobe="ffprobe", imagemagick=None))
            with patch("modular_file_utility_suite.subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 15)) as run:
                result = TaskEngine(app).inspect_metadata(source)
            self.assertIn("ffprobe_error", result)
            self.assertEqual(run.call_args.kwargs["timeout"], 15)


class TypeScriptIsolationAuditTests(unittest.TestCase):
    def test_project_cannot_copy_external_source_into_export(self):
        compiler = find_typescript_compiler()
        if compiler is None:
            self.skipTest("Native Node.js and TypeScript compiler required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside.ts"
            outside.write_text('export const secret="owned fixture outside the selected project";', encoding="utf-8")
            project = root / "project"
            (project / "src").mkdir(parents=True)
            (project / "tsconfig.json").write_text(json.dumps({
                "compilerOptions": {"module": "commonjs", "target": "ES2020"}, "include": ["src/**/*.ts"],
            }), encoding="utf-8")
            (project / "src" / "main.ts").write_text(
                "import {secret} from " + json.dumps(outside.with_suffix("").as_posix()) + "; console.log(secret);",
                encoding="utf-8",
            )
            output = root / "compiled.zip"
            with self.assertRaises(TranslationError):
                translate_project(project, output, compiler=compiler)
            self.assertFalse(output.exists())

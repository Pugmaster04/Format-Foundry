"""Hidden Tk construction/interaction checks; no full app launch or settings writes."""

import queue
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from code_translation import ProjectTranslationResult, TranslationError, TranslationResult
from language_support import LanguageLibraryError
from modular_file_utility_suite import CodeLanguagesTab, SuiteApp


class LanguageUITests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.root.withdraw()
        self.addCleanup(self.close_root)
        self.callbacks = queue.Queue()
        self.app = SimpleNamespace(
            root=self.root, _scaled=lambda value: value, reduced_motion_enabled=lambda: True,
            _register_mousewheel_target=Mock(), _register_task_cancel_event=Mock(), _unregister_task_cancel_event=Mock(),
            _terminate_processes_for_thread=Mock(), call_ui=self.callbacks.put, _open_external_url=Mock(),
            log=Mock(), info=Mock(), error=Mock(), default_output_root=Path.cwd(),
        )
        self.app._bind_responsive_wrap = lambda *args, **kwargs: SuiteApp._bind_responsive_wrap(self.app, *args, **kwargs)
        self.app._bind_flow_layout = lambda *args, **kwargs: SuiteApp._bind_flow_layout(self.app, *args, **kwargs)
        self.tab = CodeLanguagesTab(self.root, self.app)
        self.tab.pack(fill="both", expand=True)
        self.root.update_idletasks()

    def close_root(self):
        for callback in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            self.root.tk.call("after", "cancel", callback)
        self.root.destroy()

    def text(self):
        return self.tab.viewer.get("1.0", "end-1c")

    def finish_worker(self):
        self.tab.worker.join(timeout=3)
        self.assertFalse(self.tab.worker.is_alive())
        while not self.callbacks.empty():
            self.callbacks.get_nowait()()
        self.root.update_idletasks()
        self.app.error.assert_not_called()

    def test_initial_rules_are_readonly_and_no_network_opened(self):
        self.assertIn("TypeScript | Programming", self.text())
        self.assertEqual(str(self.tab.viewer.cget("state")), "disabled")
        self.assertEqual(len(self.tab.language_combo.cget("values")), 21)
        self.app._open_external_url.assert_not_called()

    def test_search_empty_result_and_recovery(self):
        self.tab.query_var.set("no-such-language")
        self.assertIn("No matching profiles", self.text())
        self.assertIn("disabled", self.tab.compare_button.state())
        self.tab.query_var.set(".rs")
        self.assertEqual(self.tab.language_var.get(), "Rust")
        self.assertIn("ownership", self.text().lower())
        self.tab.query_var.set("")
        self.assertEqual(len(self.tab.language_combo.cget("values")), 21)
        self.assertNotIn("disabled", self.tab.docs_button.state())

    def test_compare_and_return_to_rules(self):
        self.tab.language_var.set("Python")
        self.tab.target_var.set("HTML")
        self.tab.compare_button.invoke()
        self.assertIn("Different language categories", self.text())
        self.assertIn("This comparison does not generate code", self.text())
        self.tab.rules_button.invoke()
        self.assertIn("Python | Programming", self.text())

    def test_documentation_uses_existing_confirmation_policy(self):
        self.tab.docs_button.invoke()
        self.app._open_external_url.assert_called_once_with(
            "https://www.typescriptlang.org/docs/handbook/intro.html", purpose="TypeScript official documentation",
        )

    def test_generation_requires_supported_pair_and_offers_compiler_setup(self):
        self.assertNotIn("disabled", self.tab.translate_button.state())
        self.assertNotIn("disabled", self.tab.project_button.state())
        self.tab.language_var.set("Rust")
        self.tab.show_rules()
        self.assertIn("disabled", self.tab.translate_button.state())
        self.assertIn("disabled", self.tab.project_button.state())
        self.tab.language_var.set("TypeScript")
        self.tab.show_rules()
        self.tab.setup_button.invoke()
        self.app._open_external_url.assert_called_once_with(
            "https://www.typescriptlang.org/download/", purpose="TypeScript compiler setup",
        )

    def test_translation_completion_reports_saved_file_without_running_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.ts"
            output = Path(directory) / "example.js"
            source.write_text("const answer: number = 42;\n", encoding="utf-8")
            emitted = "const answer = 42;\n"
            result = TranslationResult("typescript", "javascript", output, emitted, "TypeScript compiler")
            with patch("modular_file_utility_suite.translate_code_file", return_value=result) as translate:
                self.tab.start_translation(source, output)
                self.finish_worker()
            self.assertIn("Generated example.js", self.text())
            self.assertIn(emitted.strip(), self.text())
            self.assertIn("not been run", self.text())
            self.assertIn("Saved example.js", self.tab.status_var.get())
            self.assertEqual(source.read_text(encoding="utf-8"), "const answer: number = 42;\n")
            translate.assert_called_once()

    def test_project_dialog_uses_selected_folder_and_nonoverwriting_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            (project / "tsconfig.json").write_text("{}", encoding="utf-8")
            requested = Path(directory) / "compiled.zip"
            requested.write_bytes(b"previous")
            compiler = object()
            with patch("modular_file_utility_suite.find_typescript_compiler", return_value=compiler), patch(
                "modular_file_utility_suite.filedialog.askdirectory", return_value=str(project),
            ), patch("modular_file_utility_suite.filedialog.asksaveasfilename", return_value=str(requested)), patch.object(
                self.tab, "start_project_translation",
            ) as start:
                self.tab.project_button.invoke()
            start.assert_called_once_with(project, Path(directory) / "compiled_1.zip", compiler)
            self.assertEqual(requested.read_bytes(), b"previous")

    def test_project_completion_and_failure_are_inline(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            output = Path(directory) / "compiled.zip"
            generated = ProjectTranslationResult(output, ("main.js", "math.js"), 3, "TypeScript compiler")
            with patch("modular_file_utility_suite.translate_code_project", return_value=generated) as translate:
                self.tab.start_project_translation(project, output)
                self.finish_worker()
            self.assertIn("Compiled 2 files", self.text())
            self.assertIn("math.js", self.text())
            self.assertIn("Saved compiled.zip", self.tab.status_var.get())
            translate.assert_called_once()
            with patch("modular_file_utility_suite.translate_code_project", side_effect=TranslationError("Unsupported test option")):
                self.tab.start_project_translation(project, output)
                self.finish_worker()
            self.assertIn("Unsupported test option", self.text())
            self.assertIn("no ZIP was saved", self.tab.status_var.get())

    def test_late_stop_does_not_claim_committed_project_zip_was_discarded(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "compiled.zip"
            generated = ProjectTranslationResult(output, ("main.js",), 2, "TypeScript compiler")

            def complete_after_stop(*_args, **_kwargs):
                self.tab.cancel_event.set()
                return generated

            with patch("modular_file_utility_suite.translate_code_project", side_effect=complete_after_stop):
                self.tab.start_project_translation(Path(directory), output)
                self.finish_worker()
            self.assertIn("Saved compiled.zip", self.tab.status_var.get())
            self.assertNotIn("no ZIP saved", self.tab.status_var.get())

    def test_local_inspection_returns_report_and_no_source_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private.py"
            path.write_text("private_source_value = 123\n", encoding="utf-8")
            self.tab.inspect_path(path)
            self.finish_worker()
        self.assertIn("AST parsing succeeded", self.text())
        self.assertNotIn("private_source_value", self.text())
        self.app.log.assert_not_called()
        self.assertNotIn("disabled", self.tab.inspect_button.state())
        self.assertIn("disabled", self.tab.module_cancel_button.state())

    def test_read_error_is_non_modal(self):
        with tempfile.TemporaryDirectory() as directory:
            self.tab.inspect_path(Path(directory))
            self.finish_worker()
        self.assertIn("Choose a regular file", self.text())
        self.app.info.assert_not_called()

    def test_inspection_completion_does_not_replace_new_reference_view(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("value = 1\n", encoding="utf-8")
            self.tab.inspect_path(path)
            self.tab.language_var.set("Rust")
            self.tab.show_rules()
            self.finish_worker()
        self.assertIn("Rust | Programming", self.text())
        self.assertIn("kept your current reference view", self.tab.status_var.get())

    def test_missing_library_only_disables_this_tab(self):
        with patch("modular_file_utility_suite.bundled_language_library", side_effect=LanguageLibraryError("Test: missing asset")):
            other = CodeLanguagesTab(self.root, self.app)
        self.assertIn("Other tools remain available", other.status_var.get())
        self.assertTrue(self.tab.viewer.winfo_exists())
        other.destroy()

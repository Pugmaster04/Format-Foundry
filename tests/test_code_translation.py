import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from archive_support import safe_extract_zip
from code_translation import (
    Compiler,
    TranslationCanceled,
    TranslationError,
    find_typescript_compiler,
    output_suffix,
    supported_translation,
    translate_file,
    translate_project,
)


class TranslationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fake_script = self.root / "compiler.py"
        self.fake_script.write_text(
            "import pathlib, sys, time\n"
            "args=sys.argv[1:]\n"
            "if 'WAIT' in pathlib.Path(args[0]).read_text(encoding='utf-8'): time.sleep(2)\n"
            "if 'ERROR' in pathlib.Path(args[0]).read_text(encoding='utf-8'):\n"
            " print('input.ts(1,1): error TS9999: fake diagnostic')\n"
            " raise SystemExit(2)\n"
            "out=pathlib.Path(args[args.index('--outDir')+1])\n"
            "ext={'.ts':'.js','.mts':'.mjs','.cts':'.cjs'}[pathlib.Path(args[0]).suffix]\n"
            "(out/('input'+ext)).write_text('const generated = true;\\n',encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.compiler = Compiler(Path(sys.executable), self.fake_script)

    def source(self, text="const value: number = 1;", extension=".ts"):
        path = self.root / ("input source" + extension)
        path.write_text(text, encoding="utf-8")
        return path

    def test_only_verified_pair_and_extension_are_enabled(self):
        self.assertTrue(supported_translation("typescript", "javascript"))
        for pair in (("python", "javascript"), ("javascript", "python"), ("typescript", "python")):
            self.assertFalse(supported_translation(*pair))
            with self.assertRaisesRegex(TranslationError, "no verified"):
                output_suffix(Path("file.ts"), *pair)
        for before, after in (("sample.ts", ".js"), ("sample.mts", ".mjs"), ("sample.cts", ".cjs")):
            self.assertEqual(output_suffix(Path(before), "typescript", "javascript"), after)
        with self.assertRaisesRegex(TranslationError, "TSX"):
            output_suffix(Path("page.tsx"), "typescript", "javascript")

    def test_compiler_not_present_is_actionable(self):
        source = self.source()
        with patch("code_translation.find_typescript_compiler", return_value=None), self.assertRaisesRegex(TranslationError, "Node.js"):
            translate_file(source, self.root / "output.js", "typescript", "javascript")
        self.assertFalse((self.root / "output.js").exists())

    def test_global_compiler_discovery_does_not_need_source_folder(self):
        installed_app = self.root / "installed" / "code_translation.py"
        installed_app.parent.mkdir()
        node = self.root / "node"
        node.touch()
        global_bin = self.root / "global"
        global_bin.mkdir()
        tsc_command = global_bin / "tsc.cmd"
        tsc_command.touch()
        script = global_bin / "node_modules" / "typescript" / "lib" / "tsc.js"
        script.parent.mkdir(parents=True)
        script.touch()

        def which(name):
            return {"node": str(node), "tsc": str(tsc_command)}.get(name)

        with patch("code_translation.__file__", str(installed_app)), patch("code_translation.shutil.which", side_effect=which):
            self.assertEqual(find_typescript_compiler(), Compiler(node, script.resolve()))

    def test_single_file_output_keeps_original_untouched(self):
        source = self.source()
        before = source.read_bytes()
        result = translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler)
        self.assertEqual(result.output_text.splitlines(), ["const generated = true;"])
        self.assertEqual(result.output_path.read_bytes().decode("utf-8"), result.output_text)
        self.assertEqual(source.read_bytes(), before)

    def test_module_extensions_are_kept(self):
        for before, after in ((".mts", ".mjs"), (".cts", ".cjs")):
            with self.subTest(source=before):
                source = self.source(extension=before)
                target = self.root / ("output" + after)
                self.assertEqual(translate_file(source, target, "typescript", "javascript", compiler=self.compiler).output_path, target)

    def test_failure_does_not_replace_or_leave_output(self):
        source = self.source("ERROR")
        target = self.root / "output.js"
        with self.assertRaisesRegex(TranslationError, "fake diagnostic"):
            translate_file(source, target, "typescript", "javascript", compiler=self.compiler)
        self.assertFalse(target.exists())
        target.write_text("previous", encoding="utf-8")
        with self.assertRaisesRegex(TranslationError, "already exists"):
            translate_file(source, target, "typescript", "javascript", compiler=self.compiler)
        self.assertEqual(target.read_text(encoding="utf-8"), "previous")

    def test_missing_input_bad_output_utf8_and_binary_are_rejected(self):
        source = self.source()
        with self.assertRaisesRegex(TranslationError, "must use .js"):
            translate_file(source, self.root / "bad.txt", "typescript", "javascript", compiler=self.compiler)
        with self.assertRaisesRegex(TranslationError, "regular file"):
            translate_file(self.root / "missing.ts", self.root / "output.js", "typescript", "javascript", compiler=self.compiler)
        source.write_bytes(b"\xff")
        with self.assertRaisesRegex(TranslationError, "UTF-8"):
            translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler)
        source.write_bytes(b"\0bad")
        with self.assertRaisesRegex(TranslationError, "Binary"):
            translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler)

    def test_file_size_and_source_destination_collision(self):
        source = self.source("x" * (64 * 1024 + 1))
        with self.assertRaisesRegex(TranslationError, "64 KiB"):
            translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler)
        source = self.source()
        with self.assertRaisesRegex(TranslationError, "source file"):
            translate_file(source, source, "typescript", "javascript", compiler=self.compiler)

    def test_cancel_and_timeout_leave_no_output(self):
        source = self.source("WAIT")
        stop = threading.Event()
        stop.set()
        with self.assertRaises(TranslationCanceled):
            translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler, cancel_event=stop)
        stop.clear()
        timer = threading.Timer(0.15, stop.set)
        timer.start()
        try:
            with self.assertRaises(TranslationCanceled):
                translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler, cancel_event=stop)
        finally:
            timer.join()
        self.assertFalse((self.root / "output.js").exists())
        with patch("code_translation.COMPILER_TIMEOUT_SECONDS", 0.05), self.assertRaisesRegex(TranslationError, "timed out"):
            translate_file(source, self.root / "output.js", "typescript", "javascript", compiler=self.compiler)
        self.assertFalse((self.root / "output.js").exists())


class RealTypeScriptCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = find_typescript_compiler()
        if cls.compiler is None:
            raise unittest.SkipTest("Node.js and TypeScript compiler are not installed; npm ci enables this CI test")

    def test_real_compiler_emits_js_without_running_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "real.ts"
            source.write_text(
                "export function add(a: number, b: number): number { return a + b; }\n"
                "throw new Error('Must not execute during compilation');\n", encoding="utf-8",
            )
            result = translate_file(source, root / "real.js", "typescript", "javascript", compiler=self.compiler)
            self.assertIn("function add(a, b)", result.output_text)
            self.assertIn("throw new Error", result.output_text)
            self.assertTrue(result.output_path.is_file())

    def test_real_compiler_reports_type_errors_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "broken.ts"
            source.write_text("let count: number = 'wrong';\n", encoding="utf-8")
            with self.assertRaisesRegex(TranslationError, "error TS"):
                translate_file(source, root / "broken.js", "typescript", "javascript", compiler=self.compiler)
            self.assertFalse((root / "broken.js").exists())

    def test_real_compiler_rejects_imports_that_need_a_project_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "imports.ts"
            source.write_text('import { value } from "./dependency";\nexport const result = value;\n', encoding="utf-8")
            (root / "dependency.ts").write_text("export const value = 42;\n", encoding="utf-8")
            with self.assertRaisesRegex(TranslationError, "error TS"):
                translate_file(source, root / "imports.js", "typescript", "javascript", compiler=self.compiler)
            self.assertFalse((root / "imports.js").exists())

    def test_real_compiler_preserves_mjs_cjs_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source_ext, target_ext in ((".mts", ".mjs"), (".cts", ".cjs")):
                with self.subTest(source=source_ext):
                    source = root / ("module" + source_ext)
                    source.write_text("export const answer: number = 42;\n", encoding="utf-8")
                    result = translate_file(source, root / ("module" + target_ext), "typescript", "javascript", compiler=self.compiler)
                    self.assertIn("42", result.output_text)
                    self.assertEqual(result.output_path.suffix, target_ext)
                    if target_ext == ".mjs":
                        self.assertIn("export const answer", result.output_text)
                    else:
                        self.assertIn("exports.answer", result.output_text)
                    self.assertEqual(
                        subprocess.run([str(self.compiler.node), "--check", str(result.output_path)], capture_output=True).returncode,
                        0,
                    )


class ProjectTranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        (self.project / "src").mkdir(parents=True)
        (self.project / "tsconfig.json").write_text(
            '{"compilerOptions":{"module":"commonjs","target":"ES2020"},"include":["src/**/*.ts"]}',
            encoding="utf-8",
        )
        (self.project / "src" / "main.ts").write_text("export const answer: number = 42;\n", encoding="utf-8")
        self.fake_script = self.root / "project_compiler.py"
        self.fake_script.write_text(
            "import json, pathlib, sys, time\n"
            "args=sys.argv[1:]\n"
            "config=pathlib.Path(args[args.index('--project')+1])\n"
            "root=config.parent\n"
            "source=root/'src'/'main.ts'\n"
            "if '--showConfig' in args:\n"
            " data=json.loads(config.read_text(encoding='utf-8'))\n"
            " print(json.dumps({'compilerOptions':data.get('compilerOptions',{}),'files':['./src/main.ts'],'references':data.get('references',[])}))\n"
            " raise SystemExit(0)\n"
            "if 'WAIT' in source.read_text(encoding='utf-8'): time.sleep(2)\n"
            "if 'ERROR' in source.read_text(encoding='utf-8'):\n"
            " print('src/main.ts(1,1): error TS9999: fake project error')\n"
            " raise SystemExit(2)\n"
            "out=pathlib.Path(args[args.index('--outDir')+1])\n"
            "(out/'main.js').write_text('exports.answer = 42;\\n',encoding='utf-8')\n",
            encoding="utf-8",
        )
        self.compiler = Compiler(Path(sys.executable), self.fake_script)
        self.output = self.root / "compiled.zip"

    def test_project_zip_contains_generated_files_and_preserves_source(self):
        source = self.project / "src" / "main.ts"
        original = source.read_bytes()
        result = translate_project(self.project, self.output, compiler=self.compiler)
        self.assertEqual(result.files, ("main.js",))
        self.assertEqual(result.input_file_count, 2)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ["main.js"])
            self.assertIn(b"exports.answer", archive.read("main.js"))
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse((self.project / "dist").exists())

    def test_project_requires_config_and_never_overwrites_existing_zip(self):
        (self.project / "tsconfig.json").unlink()
        with self.assertRaisesRegex(TranslationError, "tsconfig.json"):
            translate_project(self.project, self.output, compiler=self.compiler)
        (self.project / "tsconfig.json").write_text("{}", encoding="utf-8")
        self.output.write_bytes(b"original")
        with self.assertRaisesRegex(TranslationError, "already exists"):
            translate_project(self.project, self.output, compiler=self.compiler)
        self.assertEqual(self.output.read_bytes(), b"original")

    def test_project_rejects_unbounded_config_paths_and_references(self):
        config = self.project / "tsconfig.json"
        for value, match in (
            ('{"compilerOptions":{"outFile":"../escape.js"}}', "outFile"),
            ('{"compilerOptions":{"tsBuildInfoFile":"../escape.tsbuildinfo"}}', "tsBuildInfoFile"),
            ('{"compilerOptions":{"outDir":"../outside"}}', "outDir"),
            ('{"references":[{"path":"../other"}]}', "references"),
        ):
            with self.subTest(option=match):
                config.write_text(value, encoding="utf-8")
                with self.assertRaisesRegex(TranslationError, match):
                    translate_project(self.project, self.output, compiler=self.compiler)
                self.assertFalse(self.output.exists())
                self.assertFalse((self.root / "escape.js").exists())

    def test_project_limits_and_symlinks_fail_before_compile(self):
        source = self.project / "src" / "main.ts"
        source.write_text("x" * (512 * 1024 + 1), encoding="utf-8")
        with self.assertRaisesRegex(TranslationError, "oversized"):
            translate_project(self.project, self.output, compiler=self.compiler)
        source.write_text("export const answer = 42;", encoding="utf-8")
        with patch("code_translation.MAX_PROJECT_FILES", 1), self.assertRaisesRegex(TranslationError, "file compile limit"):
            translate_project(self.project, self.output, compiler=self.compiler)
        if hasattr(Path, "symlink_to"):
            link = self.project / "src" / "linked.ts"
            try:
                link.symlink_to(source)
            except OSError:
                self.skipTest("Symlink creation unavailable on this account")
            with self.assertRaisesRegex(TranslationError, "symlinks"):
                translate_project(self.project, self.output, compiler=self.compiler)
            link.unlink()
            outside = self.root / "outside.ts"
            outside.write_text("export const outside = true;\n", encoding="utf-8")
            link.symlink_to(outside)
            with patch.object(Path, "is_symlink", return_value=False), self.assertRaisesRegex(TranslationError, "symlinks"):
                translate_project(self.project, self.output, compiler=self.compiler)

    def test_project_compiler_error_cancel_and_timeout_leave_no_zip(self):
        source = self.project / "src" / "main.ts"
        source.write_text("ERROR", encoding="utf-8")
        with self.assertRaisesRegex(TranslationError, "fake project error"):
            translate_project(self.project, self.output, compiler=self.compiler)
        self.assertFalse(self.output.exists())
        source.write_text("WAIT", encoding="utf-8")
        stop = threading.Event()
        timer = threading.Timer(0.2, stop.set)
        timer.start()
        try:
            with self.assertRaises(TranslationCanceled):
                translate_project(self.project, self.output, compiler=self.compiler, cancel_event=stop)
        finally:
            timer.join()
        self.assertFalse(self.output.exists())
        with patch("code_translation.PROJECT_TIMEOUT_SECONDS", 0.05), self.assertRaisesRegex(TranslationError, "timed out"):
            translate_project(self.project, self.output, compiler=self.compiler)
        self.assertFalse(self.output.exists())


class RealTypeScriptProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler = find_typescript_compiler()
        if cls.compiler is None:
            raise unittest.SkipTest("Node.js and TypeScript compiler are not installed; npm ci enables this CI test")

    def test_commentable_tsconfig_imports_and_exclusion_compile_without_source_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            (project / "src").mkdir(parents=True)
            (project / "tsconfig.json").write_text(
                '{\n // Supported TypeScript JSONC configuration\n'
                ' "compilerOptions": {"target":"ES2020","module":"commonjs","strict":true,'
                '"rootDir":"src","outDir":"dist","sourceMap":true,},\n'
                ' "include":["src/**/*.ts"],"exclude":["src/ignored.ts"],\n}', encoding="utf-8",
            )
            (project / "src" / "math.ts").write_text(
                "export function add(a: number, b: number): number { return a + b; }\n", encoding="utf-8",
            )
            (project / "src" / "main.ts").write_text(
                'import { add } from "./math";\nconsole.log(add(2, 3));\n', encoding="utf-8",
            )
            (project / "src" / "ignored.ts").write_text("let bad: number = 'wrong';\n", encoding="utf-8")
            before = {path.relative_to(project): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            result = translate_project(project, root / "compiled.zip", compiler=self.compiler)
            self.assertEqual(result.files, ("main.js", "math.js"))
            self.assertFalse((project / "dist").exists())
            self.assertEqual(before, {path.relative_to(project): path.read_bytes() for path in project.rglob("*") if path.is_file()})
            extracted = root / "extracted"
            with zipfile.ZipFile(result.output_path) as archive:
                self.assertEqual(sorted(archive.namelist()), ["main.js", "math.js"])
            safe_extract_zip(result.output_path, extracted)
            run = subprocess.run(
                [str(self.compiler.node), str(extracted / "main.js")], cwd=extracted, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "5")

    def test_project_type_errors_leave_no_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (project / "tsconfig.json").write_text('{"compilerOptions":{"strict":true}}', encoding="utf-8")
            (project / "bad.ts").write_text("let count: number = 'wrong';\n", encoding="utf-8")
            with self.assertRaisesRegex(TranslationError, "error TS"):
                translate_project(project, root / "compiled.zip", compiler=self.compiler)
            self.assertFalse((root / "compiled.zip").exists())

    def test_local_config_extends_and_unsafe_outfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            (project / "config").mkdir(parents=True)
            (project / "config" / "base.json").write_text(
                '{"compilerOptions":{"target":"ES2020","module":"commonjs","strict":true}}', encoding="utf-8",
            )
            config = project / "tsconfig.json"
            config.write_text('{"extends":"./config/base.json","include":["src/**/*.ts"]}', encoding="utf-8")
            (project / "src").mkdir()
            (project / "src" / "main.ts").write_text("export const value: number = 7;\n", encoding="utf-8")
            result = translate_project(project, root / "compiled.zip", compiler=self.compiler)
            self.assertEqual(result.files, ("main.js",))
            (root / "compiled.zip").unlink()
            (project / "config" / "base.json").write_text(
                '{"compilerOptions":{"target":"ES2020","module":"amd","outFile":"../../escape.js"}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TranslationError, "outFile"):
                translate_project(project, root / "compiled.zip", compiler=self.compiler)
            self.assertFalse((root / "compiled.zip").exists())
            self.assertFalse((root / "escape.js").exists())

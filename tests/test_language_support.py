import ast
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import language_support as languages

ROOT = Path(__file__).resolve().parents[1]


class LanguageLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = languages.load_language_library()
        cls.document = json.loads(languages.LIBRARY_PATH.read_text(encoding="utf-8"))

    def load_document(self, document):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return languages.load_language_library(path)

    def test_profile_coverage_and_formatting(self):
        self.assertEqual(len(self.library.profiles), 21)
        self.assertEqual({p.id for p in self.library.profiles}, {
            "python", "javascript", "typescript", "java", "c", "cpp", "csharp", "go", "rust", "swift", "kotlin",
            "php", "ruby", "r", "bash", "powershell", "sql", "dart", "lua", "html", "css",
        })
        for profile in self.library.profiles:
            with self.subTest(language=profile.name):
                self.assertEqual(len(profile.rules), len(languages.RULE_TOPICS))
                report = languages.format_profile(profile, self.library.revision)
                self.assertIn(profile.example, report)
                self.assertIn(profile.reference_url, report)
                self.assertIn("not a complete grammar", report)
                self.assertIn("not proof of language", report)

    def test_categorizes_non_programming_languages(self):
        profiles = {p.id: p for p in self.library.profiles}
        for identifier, category in (("html", "Markup"), ("css", "Stylesheet"), ("sql", "Query"), ("bash", "Shell")):
            self.assertEqual(profiles[identifier].category, category)

    def test_search_by_name_alias_extension_and_rules(self):
        for query, expected in (("PyThOn", "python"), ("golang", "go"), (".RS", "rust"), ("ownership", "rust"),
                                ("typescript nullable", "typescript"), ("stylesheet", "css")):
            with self.subTest(query=query):
                self.assertIn(expected, {p.id for p in self.library.search(query)})
        self.assertEqual(self.library.search("no-such-language"), ())
        self.assertEqual(self.library.search("   "), self.library.profiles)

    def test_extension_hints_are_ambiguous_and_case_insensitive(self):
        self.assertEqual({p.id for p in self.library.candidates("header.h")}, {"c", "cpp"})
        self.assertEqual([p.id for p in self.library.candidates("source.PY")], ["python"])
        self.assertEqual(self.library.candidates("unknown.secret"), ())
        self.assertEqual(self.library.candidates("README"), ())

    def test_comparison_has_no_conversion_claim(self):
        source, target = self.library.profiles[:2]
        report = languages.compare_languages(source, target)
        self.assertIn("This comparison does not generate code", report)
        for topic in languages.RULE_TOPICS:
            self.assertIn(source.rule(topic), report)
            self.assertIn(target.rule(topic), report)
        self.assertIn("Verification checklist", report)

    def test_same_language_and_different_category_warnings(self):
        source = self.library.profiles[0]
        self.assertIn("Same language", languages.compare_languages(source, source))
        self.assertIn("Different language categories", languages.compare_languages(source, self.library.profiles[-1]))

    def test_asset_load_is_independent_of_working_directory(self):
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                self.assertEqual(len(languages.load_language_library().profiles), 21)
            finally:
                os.chdir(before)

    def test_cached_profiles_are_immutable(self):
        self.assertIs(languages.bundled_language_library(), languages.bundled_language_library())
        with self.assertRaises(AttributeError):
            self.library.profiles[0].name = "Changed"

    def test_rejects_invalid_schemas_and_empty_profiles(self):
        for version in (True, "1", 2, None):
            document = copy.deepcopy(self.document)
            document["schema_version"] = version
            with self.subTest(version=version), self.assertRaises(languages.LanguageLibraryError):
                self.load_document(document)
        for document in ([], {}, {**self.document, "extra": 1}, {**self.document, "languages": []}):
            with self.assertRaises(languages.LanguageLibraryError):
                self.load_document(document)

    def test_rejects_duplicate_id_or_name(self):
        for field in ("id", "name"):
            document = copy.deepcopy(self.document)
            document["languages"][1][field] = document["languages"][0][field]
            with self.subTest(field=field), self.assertRaises(languages.LanguageLibraryError):
                self.load_document(document)

    def test_rejects_incomplete_rules_or_bad_profile_fields(self):
        for field, value in (("category", "Unclassified"), ("rules", {}), ("extensions", ["py"]),
                             ("extensions", [".py", ".py"]), ("example", ""), ("pitfalls", []), ("id", "../../file")):
            document = copy.deepcopy(self.document)
            document["languages"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(languages.LanguageLibraryError):
                self.load_document(document)

    def test_rejects_non_https_credentialed_or_malformed_reference_links(self):
        for url in ("http://example.com", "file:///tmp/input", "javascript:alert(1)", "https://user:password@example.com",
                    "https:///missing-host", "https://example.com:443/", "https://example.com:bad/", "https://["):
            document = copy.deepcopy(self.document)
            document["languages"][0]["reference_url"] = url
            with self.subTest(url=url), self.assertRaises(languages.LanguageLibraryError):
                self.load_document(document)

    def test_missing_corrupt_duplicate_and_oversized_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library.json"
            with self.assertRaises(languages.LanguageLibraryError):
                languages.load_language_library(path)
            for data in (b"not json", b'{"schema_version":1,"schema_version":1}', b" " * (languages.MAX_LIBRARY_BYTES + 1)):
                path.write_bytes(data)
                with self.assertRaises(languages.LanguageLibraryError):
                    languages.load_language_library(path)

    def test_packaging_includes_library_on_both_specs(self):
        for name in ("FormatFoundry.spec", "FormatFoundry_Portable.spec"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
            datas = ast.literal_eval(next(item.value for item in analysis.keywords if item.arg == "datas"))
            self.assertIn(("assets/code_languages.json", "assets"), datas)
        self.assertIn("FormatFoundry.spec", (ROOT / "build_linux.sh").read_text(encoding="utf-8"))


class SourceInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.library = languages.bundled_language_library()

    def inspect(self, content, name="example.py"):
        path = self.root / name
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        original = path.read_bytes()
        report = languages.inspect_source(path, self.library)
        self.assertEqual(path.read_bytes(), original)
        return report

    def test_python_parse_success_without_execution_or_source_leak(self):
        marker = self.root / "must-not-exist.txt"
        source = f"from pathlib import Path\nPath({str(marker)!r}).write_text('side effect')\nsecret = 'sensitive-value-123'\n"
        with patch("builtins.exec", side_effect=AssertionError("Source must never execute")):
            report = self.inspect(source)
        self.assertIn("AST parsing succeeded", report)
        self.assertIn("does not check scope", report)
        self.assertNotIn("sensitive-value-123", report)
        self.assertNotIn("example.py", report)
        self.assertNotIn(str(self.root), report)
        self.assertFalse(marker.exists())

    def test_python_parse_error_has_location_without_source(self):
        report = self.inspect("def sensitive_name(\n")
        self.assertIn("AST parse failed at line 1", report)
        self.assertNotIn("sensitive_name", report)

    def test_python_parser_limits_report_failure(self):
        with patch.object(languages.ast, "parse", side_effect=RecursionError):
            self.assertIn("parser limits", self.inspect("x=1"))

    def test_utf8_bom_and_empty_file(self):
        self.assertIn("AST parsing succeeded", self.inspect(b"\xef\xbb\xbfprint('hello')\n"))
        self.assertIn("Lines: 0", self.inspect(""))

    def test_other_languages_never_use_python_parser(self):
        with patch.object(languages.ast, "parse", side_effect=AssertionError("Not Python")):
            report = self.inspect("function deliberately incomplete", "broken.js")
        self.assertIn("JavaScript", report)
        self.assertIn("no syntax parser", report)
        self.assertNotIn("succeeded", report)

    def test_ambiguous_and_unknown_files_are_not_misclassified(self):
        self.assertIn("Ambiguous extension", self.inspect("int x;", "header.h"))
        self.assertIn("Extension hints: Unknown", self.inspect("plain text", "note.txt"))

    def test_markup_is_not_rendered(self):
        report = self.inspect('<script>fetch("https://example.com/secret")</script>', "page.html")
        self.assertIn("HTML", report)
        self.assertNotIn("<script>", report)
        self.assertIn("never", languages.format_profile(self.library.candidates("page.html")[0], self.library.revision))

    def test_rejects_oversize_binary_encoding_and_control_characters(self):
        for content, message in ((b"x" * (languages.MAX_SOURCE_BYTES + 1), "64 KiB"), (b"\0binary", "Binary"),
                                 (b"\xff", "UTF-8"), (b"\x1b[31m", "control-character")):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.inspect(content)

    def test_rejects_directories_and_missing_files(self):
        for path in (self.root, self.root / "missing.py"):
            with self.assertRaisesRegex(ValueError, "regular file"):
                languages.inspect_source(path, self.library)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO check")
    def test_rejects_fifo_without_blocking(self):
        path = self.root / "pipe.py"
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, "regular file"):
            languages.inspect_source(path, self.library)

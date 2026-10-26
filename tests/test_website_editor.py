"""Regression tests for bounded theme saves and authenticated local publication."""

from __future__ import annotations

import http.client
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from tools import website_editor, website_theme

ROOT = Path(__file__).resolve().parents[1]


def fixture(root: Path) -> None:
    docs = root / "docs"
    docs.mkdir()
    (docs / "theme.json").write_text(website_theme.theme_json(website_theme.DEFAULT_THEME), encoding="utf-8")
    (docs / "theme.css").write_text(website_theme.render_theme_css(website_theme.DEFAULT_THEME), encoding="utf-8")
    (docs / "index.html").write_text("<h1>Format Foundry</h1>", encoding="utf-8")


class ThemeTests(unittest.TestCase):
    def test_rejects_injection_unknown_fields_and_invalid_types(self) -> None:
        invalid = [
            {"background": "red; background:url(https://invalid.test/)"},
            {"bodyFont": "url(https://invalid.test/font)"}, {"headingFont": "__proto__"},
            {"textSize": True}, {"textSize": 16.0}, {"contentWidth": 20000},
            {"sectionSpacing": float("nan")}, {"showGrid": "false"},
            {"schemaVersion": True}, {"extra": "unsupported"},
        ]
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                website_theme.validate_theme({**website_theme.DEFAULT_THEME, **overrides})
        with self.assertRaises(ValueError):
            website_theme.validate_theme({})

    def test_canonical_order_and_color_normalization(self) -> None:
        reordered = dict(reversed(list(website_theme.DEFAULT_THEME.items())))
        reordered["accent"] = "#1FA58E"
        self.assertEqual(website_theme.theme_json(reordered), website_theme.theme_json(website_theme.DEFAULT_THEME))

    def test_checked_in_theme_files_match_generator(self) -> None:
        theme = json.loads((ROOT / "docs/theme.json").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / "docs/theme.css").read_text(encoding="utf-8"), website_theme.render_theme_css(theme))

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_browser_and_saved_css_match_for_all_presets_and_boundaries(self) -> None:
        script = """
const api = require('./docs/theme.js');
const themes = Object.values(api.presets).map(preset => preset.theme);
for (const [key, limits] of Object.entries(api.bounds)) {
  for (const value of limits) themes.push({...api.defaults, [key]: value});
}
themes.push({...api.defaults, background:'#FFFFFF', accent:'#000000', highlight:'#000000'});
process.stdout.write(JSON.stringify(themes.map(theme => ({theme, css:api.css(theme)}))));
"""
        result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True, check=True, timeout=20)
        for item in json.loads(result.stdout):
            with self.subTest(theme=item["theme"]):
                self.assertEqual(website_theme.render_theme_css(item["theme"]), item["css"])


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.store = website_editor.ThemeStore(self.root)

    def test_save_backs_up_previous_files_and_preserves_page_content(self) -> None:
        original = {name: (self.root / "docs" / name).read_bytes() for name in ("theme.json", "theme.css")}
        theme = {**website_theme.DEFAULT_THEME, "accent": "#abcdef"}
        backup = self.store.save(theme)
        with zipfile.ZipFile(self.root / backup) as archive:
            self.assertEqual(set(archive.namelist()), set(original))
            for name, content in original.items():
                self.assertEqual(archive.read(name), content)
        self.assertEqual(self.store.load(), theme)
        self.assertEqual((self.root / "docs/theme.css").read_text(), website_theme.render_theme_css(theme))
        self.assertEqual((self.root / "docs/index.html").read_text(), "<h1>Format Foundry</h1>")
        self.assertEqual(self.store.save(theme), "")
        self.assertEqual(len(list((self.root / "build/website-theme-backups").glob("*.zip"))), 1)

    def test_partial_write_failure_restores_both_files(self) -> None:
        originals = {name: (self.root / "docs" / name).read_bytes() for name in ("theme.json", "theme.css")}
        original_write = website_editor._atomic_write
        calls = 0

        def fail_second_write(path: Path, data: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated full disk")
            original_write(path, data)

        with patch.object(website_editor, "_atomic_write", side_effect=fail_second_write), self.assertRaises(OSError):
            self.store.save({**website_theme.DEFAULT_THEME, "accent": "#abcdef"})
        for name, content in originals.items():
            self.assertEqual((self.root / "docs" / name).read_bytes(), content)

    def test_invalid_settings_never_create_a_backup_or_change_files(self) -> None:
        before = (self.root / "docs/theme.json").read_bytes()
        with self.assertRaises(ValueError):
            self.store.save({**website_theme.DEFAULT_THEME, "accent": "</style><script>"})
        self.assertEqual((self.root / "docs/theme.json").read_bytes(), before)
        self.assertFalse((self.root / "build").exists())

    def test_refuses_a_link_outside_website_folder(self) -> None:
        target = self.root / "outside.txt"
        target.write_text("preserve me")
        path = self.root / "docs/theme.css"
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"Symlinks unavailable: {exc}")
        with self.assertRaises(ValueError):
            self.store.save(website_theme.DEFAULT_THEME)
        self.assertEqual(target.read_text(), "preserve me")


class PublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.publisher = website_editor.GitHubPublisher(ROOT)
        self.head, self.base_tree, self.tree, self.commit = (char * 40 for char in "abcd")

    def responses(self) -> list[dict[str, Any]]:
        return [{"object": {"sha": self.head}}, {"tree": {"sha": self.base_tree}}, {"sha": self.tree}, {"sha": self.commit}, {}]

    def test_publication_updates_only_validated_appearance_files_without_force(self) -> None:
        with patch.object(self.publisher, "api", side_effect=self.responses()) as api:
            result = self.publisher.publish(website_theme.DEFAULT_THEME)
        self.assertEqual(result["commit"], self.commit)
        tree_request = api.call_args_list[2].args
        self.assertEqual(tree_request[0], "git/trees")
        self.assertEqual(tree_request[1]["base_tree"], self.base_tree)
        self.assertEqual({item["path"] for item in tree_request[1]["tree"]}, {"docs/theme.json", "docs/theme.css"})
        self.assertEqual(api.call_args_list[3].args[1]["parents"], [self.head])
        self.assertEqual(api.call_args_list[4].args, ("git/refs/heads/main", {"sha": self.commit, "force": False}, "PATCH"))

    def test_unchanged_appearance_does_not_create_a_commit(self) -> None:
        replies = self.responses()[:3]
        replies[2] = {"sha": self.base_tree}
        with patch.object(self.publisher, "api", side_effect=replies) as api:
            result = self.publisher.publish(website_theme.DEFAULT_THEME)
        self.assertTrue(result["unchanged"])
        self.assertEqual(api.call_count, 3)

    def test_remote_branch_race_fails_without_retrying_force(self) -> None:
        with patch.object(self.publisher, "api", side_effect=[*self.responses()[:4], RuntimeError("Reference moved")]) as api:
            with self.assertRaises(RuntimeError):
                self.publisher.publish(website_theme.DEFAULT_THEME)
        self.assertEqual(api.call_count, 5)
        self.assertFalse(api.call_args.args[1]["force"])

    def test_deployment_status_requires_matching_successful_revision(self) -> None:
        runs = [
            [{"head_sha": self.head, "status": "completed", "conclusion": "success"}],
            [{"head_sha": self.commit, "status": "in_progress"}],
            [{"head_sha": self.commit, "status": "completed", "conclusion": "failure"}],
            [{"head_sha": self.commit, "status": "completed", "conclusion": "success"}],
        ]
        for items, expected in zip(runs, ("pending", "pending", "failed", "live"), strict=True):
            with self.subTest(expected=expected), patch.object(self.publisher, "api", return_value={"workflow_runs": items}):
                self.assertEqual(self.publisher.status(self.commit)["state"], expected)


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture(self.root)
        self.server = website_editor.EditorServer(self.root)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str, *, body: Any = None, token: bool = True, origin: str | None = "valid", host: str | None = None) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-FormatFoundry-Editor-Token"] = self.server.token
        if origin:
            headers["Origin"] = self.server.origin if origin == "valid" else origin
        if host:
            headers["Host"] = host
        try:
            connection.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_save_requires_token_same_origin_and_expected_host(self) -> None:
        body = {"theme": {**website_theme.DEFAULT_THEME, "accent": "#abcdef"}}
        for options in ({"token": False}, {"origin": None}, {"origin": "https://evil.invalid"}, {"host": "evil.invalid"}):
            with self.subTest(options=options):
                self.assertEqual(self.request("POST", "/api/save", body=body, **options)[0], 403)
        self.assertEqual(self.server.store.load(), website_theme.DEFAULT_THEME)
        status, data = self.request("POST", "/api/save", body=body)
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data)["backupCreated"])
        self.assertEqual(self.server.store.load()["accent"], "#abcdef")

    def test_state_is_private_but_preview_is_public(self) -> None:
        self.assertEqual(self.request("GET", "/api/state", token=False)[0], 403)
        self.assertEqual(self.request("GET", "/api/state", origin=None)[0], 200)
        status, data = self.request("GET", "/index.html", token=False, origin=None)
        self.assertEqual(status, 200)
        self.assertIn(b"Format Foundry", data)
        self.assertEqual(self.request("GET", "/build/", token=False)[0], 404)

    def test_rejects_oversized_unknown_and_invalid_settings(self) -> None:
        for path, body in (("/api/save", {"theme": {}}), ("/api/save", {"theme": "x" * 20000}), ("/api/unknown", {"theme": website_theme.DEFAULT_THEME})):
            with self.subTest(path=path, body_length=len(str(body))):
                self.assertEqual(self.request("POST", path, body=body)[0], 400)
        self.assertEqual(self.request("GET", "/api/publication?commit=" + "a" * 40)[0], 400)

    def test_publish_failure_reports_that_local_files_were_saved(self) -> None:
        theme = {**website_theme.DEFAULT_THEME, "accent": "#abcdef"}
        with patch.object(self.server.publisher, "publish", side_effect=RuntimeError("Not signed in")):
            status, data = self.request("POST", "/api/publish", body={"theme": theme})
        self.assertEqual(status, 400)
        self.assertTrue(json.loads(data)["saved"])
        self.assertEqual(self.server.store.load(), theme)


if __name__ == "__main__":
    unittest.main()

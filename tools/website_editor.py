"""Open the local website appearance editor with authenticated save/publish controls."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import webbrowser
import zipfile
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .website_theme import DEFAULT_THEME, render_theme_css, theme_json, validate_theme

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Pugmaster04/Format-Foundry"
LIVE_URL = "https://pugmaster04.github.io/Format-Foundry/"
MAX_BODY = 16 * 1024


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".appearance-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class ThemeStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.docs = self.root / "docs"
        if self.docs.is_symlink() or self.docs.resolve().parent != self.root:
            raise ValueError("The website folder must be inside this project.")
        self.lock = threading.Lock()

    def load(self) -> dict[str, Any]:
        path = self.docs / "theme.json"
        if path.stat().st_size > MAX_BODY:
            raise ValueError("The saved appearance file exceeds its size limit.")
        return validate_theme(json.loads(path.read_text(encoding="utf-8-sig")))

    def save(self, theme: Any) -> str:
        normalized = validate_theme(theme)
        files = {"theme.json": theme_json(normalized).encode(), "theme.css": render_theme_css(normalized).encode()}
        with self.lock:
            previous: dict[str, bytes | None] = {}
            for name in files:
                path = self.docs / name
                if path.is_symlink() or path.resolve().parent != self.docs.resolve():
                    raise ValueError("Appearance files must be regular files in the website folder.")
                if path.exists() and (not path.is_file() or path.stat().st_size > 1024 * 1024):
                    raise ValueError("An existing appearance file cannot be safely backed up.")
                previous[name] = path.read_bytes() if path.exists() else None
            if previous == files:
                return ""
            directory = self.root / "build" / "website-theme-backups"
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = directory / f"theme-{stamp}-{secrets.token_hex(4)}.zip"
            with zipfile.ZipFile(backup, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, content in previous.items():
                    if content is not None:
                        archive.writestr(name, content)
            try:
                for name, content in files.items():
                    _atomic_write(self.docs / name, content)
            except OSError:
                for name, content in previous.items():
                    if content is None:
                        (self.docs / name).unlink(missing_ok=True)
                    else:
                        _atomic_write(self.docs / name, content)
                raise
            return str(backup.relative_to(self.root))


class GitHubPublisher:
    """Publish only the two validated appearance files in one non-forced commit."""

    def __init__(self, root: Path):
        self.root = root
        self.executable = shutil.which("gh")

    def api(self, endpoint: str, payload: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
        if not self.executable:
            raise RuntimeError("Publishing needs GitHub sign-in on this computer. Install the GitHub CLI and run gh auth login once.")
        command = [self.executable, "api", f"repos/{REPOSITORY}/{endpoint}", "--method", method]
        if payload is not None:
            command += ["--input", "-"]
        completed = subprocess.run(
            command, input=json.dumps(payload) if payload is not None else None, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=30, cwd=self.root, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode:
            raise RuntimeError("GitHub could not complete publication: " + completed.stderr.strip()[:600])
        result = json.loads(completed.stdout)
        if not isinstance(result, dict):
            raise RuntimeError("GitHub returned an unexpected response.")
        return result

    @staticmethod
    def sha(value: Any) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
            raise RuntimeError("GitHub returned an invalid revision identifier.")
        return value

    def publish(self, theme: Any) -> dict[str, Any]:
        normalized = validate_theme(theme)
        head = self.sha(self.api("git/ref/heads/main")["object"]["sha"])
        base_tree = self.sha(self.api(f"git/commits/{head}")["tree"]["sha"])
        files = {"docs/theme.json": theme_json(normalized), "docs/theme.css": render_theme_css(normalized)}
        tree = self.sha(self.api("git/trees", {
            "base_tree": base_tree,
            "tree": [{"path": path, "mode": "100644", "type": "blob", "content": content} for path, content in files.items()],
        }, "POST")["sha"])
        if tree == base_tree:
            return {"commit": head, "unchanged": True, "url": LIVE_URL}
        commit = self.sha(self.api("git/commits", {
            "message": "Update website appearance", "tree": tree, "parents": [head],
        }, "POST")["sha"])
        self.api("git/refs/heads/main", {"sha": commit, "force": False}, "PATCH")
        return {"commit": commit, "unchanged": False, "url": LIVE_URL}

    def status(self, commit: str) -> dict[str, str]:
        self.sha(commit)
        runs = self.api("actions/workflows/deploy-website.yml/runs?branch=main&event=push&per_page=10")
        run = next((item for item in runs.get("workflow_runs", []) if item.get("head_sha") == commit), None)
        if run is None:
            return {"state": "pending", "message": "Waiting for website publication to start."}
        if run.get("status") != "completed":
            return {"state": "pending", "message": "Website publication is running."}
        if run.get("conclusion") == "success":
            return {"state": "live", "message": "Your appearance is live.", "url": LIVE_URL}
        return {"state": "failed", "message": "Website publication needs attention on GitHub.", "url": str(run.get("html_url") or LIVE_URL)}


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root: Path, port: int = 0, publisher: GitHubPublisher | None = None):
        self.store = ThemeStore(root)
        self.token = secrets.token_urlsafe(32)
        self.publisher = publisher or GitHubPublisher(root)
        self.published: set[str] = set()
        self.publish_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), EditorHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    @property
    def editor_url(self) -> str:
        return f"{self.origin}/appearance.html#editor={self.token}"


class EditorHandler(SimpleHTTPRequestHandler):
    server: EditorServer

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(args[2].store.docs), **kwargs)

    def log_message(self, _format: str, *_args: Any) -> None:
        pass  # Local control tokens and owner interactions are not logged.

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def json_response(self, status: int, value: dict[str, Any]) -> None:
        data = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self) -> bool:
        return self.headers.get("Host") == urlsplit(self.server.origin).netloc

    def authorized(self, *, writing: bool = False) -> bool:
        token = self.headers.get("X-FormatFoundry-Editor-Token", "")
        origin = self.headers.get("Origin")
        return self.valid_host() and hmac.compare_digest(token, self.server.token) and (
            origin == self.server.origin if writing else origin in {None, self.server.origin}
        )

    def do_GET(self) -> None:
        if not self.valid_host():
            self.json_response(403, {"error": "Invalid local editor host."})
            return
        route = urlsplit(self.path)
        if route.path.startswith("/api/"):
            if not self.authorized():
                self.json_response(403, {"error": "Open the editor through its project launcher."})
                return
            try:
                if route.path == "/api/state":
                    warning = ""
                    try:
                        theme = self.server.store.load()
                    except (OSError, ValueError):
                        theme = dict(DEFAULT_THEME)
                        warning = "The saved appearance could not be loaded. Its original files will be backed up before saving."
                    self.json_response(200, {"theme": theme, "canSave": True, "canPublish": bool(self.server.publisher.executable), "warning": warning})
                elif route.path == "/api/publication":
                    commit = parse_qs(route.query).get("commit", [""])[0]
                    if commit not in self.server.published:
                        raise ValueError("Unknown publication.")
                    self.json_response(200, self.server.publisher.status(commit))
                else:
                    self.json_response(404, {"error": "Unknown editor operation."})
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                self.json_response(400, {"error": str(exc)})
            return
        path = Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(self.server.store.docs.resolve()):
            self.send_error(403)
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if not self.valid_host():
            self.send_error(403)
            return
        path = Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(self.server.store.docs.resolve()):
            self.send_error(403)
            return
        super().do_HEAD()

    def list_directory(self, _path: str | os.PathLike[str]) -> None:
        self.send_error(404)
        return None

    def do_POST(self) -> None:
        if not self.authorized(writing=True):
            self.json_response(403, {"error": "This editor request is not authorized."})
            return
        saved = False
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or self.headers.get_content_type() != "application/json":
                raise ValueError("Send a small JSON appearance document.")
            self.connection.settimeout(10)
            body = json.loads(self.rfile.read(size))
            route = urlsplit(self.path).path
            if route == "/api/close" and body == {}:
                self.json_response(200, {"closed": True})
                self.wfile.flush()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if route not in {"/api/save", "/api/publish"} or not isinstance(body, dict) or set(body) != {"theme"}:
                raise ValueError("Unknown editor operation or unsupported settings.")
            theme = validate_theme(body["theme"])
            if route == "/api/publish" and not self.server.publish_lock.acquire(blocking=False):
                self.json_response(409, {"error": "A publication is already running."})
                return
            try:
                backup = self.server.store.save(theme)
                saved = True
                result: dict[str, Any] = {"saved": True, "backupCreated": bool(backup)}
                if route == "/api/publish":
                    result.update(self.server.publisher.publish(theme))
                    self.server.published.add(result["commit"])
                self.json_response(200, result)
            finally:
                if route == "/api/publish":
                    self.server.publish_lock.release()
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            self.json_response(400, {"error": str(exc), "saved": saved})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="Run without opening the browser")
    parser.add_argument("--port", type=int, default=0, help="Local port; the default chooses a free port")
    args = parser.parse_args()
    server = EditorServer(ROOT, args.port)
    print(f"Website appearance editor running on {server.origin}. Use Close editor when finished.", flush=True)
    if not args.no_browser:
        webbrowser.open(server.editor_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

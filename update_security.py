"""Bounded, policy-checked update transport and verified atomic downloads."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from file_operation_support import commit_output, file_identity
from support_runtime import validate_trusted_remote_url

MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024


def validate_url(url: str, *, require_https: bool, trusted_hosts: tuple[str, ...] | None) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ({"https"} if require_https else {"https", "http"}) or not parsed.hostname:
        raise ValueError("Update URL violates the HTTP/HTTPS policy.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials in update URLs are not allowed.")
    if trusted_hosts is not None:
        allowed, reason = validate_trusted_remote_url(url, trusted_hosts)
        if not allowed:
            raise ValueError(reason)


class PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, validate: Callable[[str], None]):
        self.validate = validate

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        self.validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def policy_opener(*, require_https: bool, trusted_hosts: tuple[str, ...] | None) -> Callable[..., Any]:
    def validate(url: str) -> None:
        validate_url(url, require_https=require_https, trusted_hosts=trusted_hosts)

    opener = urllib.request.build_opener(PolicyRedirectHandler(validate))

    def open_request(request: urllib.request.Request, **kwargs: Any) -> Any:
        validate(request.full_url)
        return opener.open(request, **kwargs)

    return open_request


def download_verified(
    request: urllib.request.Request,
    target: Path,
    expected_sha256: str,
    *,
    opener: Callable[..., Any],
    progress: Callable[[int], None] = lambda _percent: None,
    check_cancelled: Callable[[], None] = lambda: None,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> str:
    if expected_sha256 and (len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256)):
        raise ValueError("Invalid SHA256 digest.")
    previous = file_identity(target)
    fd, name = tempfile.mkstemp(prefix=".foundry-download-", suffix=".part", dir=target.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as output, opener(request, timeout=30) as response:
            header = response.headers.get("Content-Length", "")
            total = int(header) if header.isdigit() else 0
            if total > max_bytes:
                raise ValueError("Update exceeds the download size limit.")
            read = 0
            last_percent = -1
            digest = hashlib.sha256()
            while True:
                check_cancelled()
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                read += len(chunk)
                if read > max_bytes:
                    raise ValueError("Update exceeds the download size limit.")
                output.write(chunk)
                digest.update(chunk)
                percent = min(99, int(read * 100 / total)) if total else 0
                if percent != last_percent:
                    progress(percent)
                    last_percent = percent
            if not read or (total and total != read):
                raise ValueError("Update download is empty or incomplete.")
            actual = digest.hexdigest()
            if expected_sha256 and actual != expected_sha256:
                raise ValueError("Downloaded file failed SHA256 verification. Existing files were preserved.")
            output.flush()
            os.fsync(output.fileno())
        check_cancelled()
        commit_output(staged, target, previous)
        return actual
    finally:
        staged.unlink(missing_ok=True)

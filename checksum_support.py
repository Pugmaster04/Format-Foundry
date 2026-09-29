from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path


def hash_file(path: Path, algorithm: str = "sha256", check_cancelled: Callable[[], None] = lambda: None) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        while True:
            check_cancelled()
            chunk = source.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def verify_checksums(report: Path, algorithm: str, check_cancelled: Callable[[], None] = lambda: None) -> tuple[int, list[str]]:
    digest_length = hashlib.new(algorithm).digest_size * 2
    entries = []
    if report.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Checksum report exceeds the 16 MiB limit.")
    for number, line in enumerate(report.read_text(encoding="utf-8-sig").splitlines(), 1):
        check_cancelled()
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([0-9a-fA-F]+) [ *](.+)", line)
        if not match or len(match[1]) != digest_length:
            raise ValueError(f"Invalid {algorithm} checksum entry on line {number}.")
        path = Path(match[2])
        entries.append((match[1].lower(), path if path.is_absolute() else report.parent / path))
    if not entries:
        raise ValueError("The report contains no checksum entries.")
    checked, issues = 0, []
    for expected, path in entries:
        check_cancelled()
        if not path.is_file():
            issues.append(f"Missing: {path}")
            continue
        actual = hash_file(path, algorithm, check_cancelled)
        checked += 1
        if actual != expected:
            issues.append(f"Mismatch: {path}")
    return checked, issues

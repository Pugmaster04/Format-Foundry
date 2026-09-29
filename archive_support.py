from __future__ import annotations

import os
import shutil
import stat
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from file_operation_support import commit_output, file_identity

MAX_ARCHIVE_MEMBERS = 500_000


def _safe_member_target(destination: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    destination_root = destination.resolve()
    target = (destination_root / normalized).resolve()
    if PureWindowsPath(member_name).drive or normalized.startswith("/") or ":" in normalized or ".." in Path(normalized).parts:
        raise RuntimeError(f"Archive member escapes the destination: {member_name}")
    try:
        target.relative_to(destination_root)
    except ValueError as exc:
        raise RuntimeError(f"Archive member escapes the destination: {member_name}") from exc
    return target


def copy_cancelable(source: BinaryIO, target: BinaryIO, check_cancelled: Callable[[], None]) -> None:
    while True:
        check_cancelled()
        chunk = source.read(1024 * 1024)
        if not chunk:
            return
        target.write(chunk)


def _ensure_archive_fits(destination: Path, total_size: int) -> None:
    if total_size > shutil.disk_usage(destination).free:
        raise RuntimeError("Archive contents exceed the free space available in the destination.")


def _extract(archive_path: Path, destination: Path, kind: str, check: Callable[[], None]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(destination):
        raise FileExistsError(f"Extract into a new directory to preserve existing files: {destination}")
    with tempfile.TemporaryDirectory(prefix=".foundry-extract-", dir=destination.parent) as raw_stage:
        stage = Path(raw_stage) / "contents"
        stage.mkdir()
        archive = zipfile.ZipFile(archive_path) if kind == "zip" else tarfile.open(archive_path, "r:*")
        with archive:
            members = archive.infolist() if kind == "zip" else archive.getmembers()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise RuntimeError("Archive contains too many entries.")
            entries = []
            reserved: set[str] = set()
            total = 0
            for member in members:
                check()
                if kind == "zip":
                    name, size, directory = member.filename, member.file_size, member.is_dir()
                    if stat.S_ISLNK(member.external_attr >> 16):
                        raise RuntimeError(f"Symbolic links are not allowed in ZIP archives: {name}")
                else:
                    name, size, directory = member.name, member.size, member.isdir()
                    if not (member.isfile() or directory):
                        raise RuntimeError(f"Links and special files are not allowed in TAR archives: {name}")
                target = _safe_member_target(stage, name)
                key = os.path.normcase(str(target))
                if key in reserved:
                    raise RuntimeError(f"Duplicate archive member: {name}")
                reserved.add(key)
                total += max(0, size)
                entries.append((member, target, directory))
            _ensure_archive_fits(stage, total)
            for member, target, directory in entries:
                check()
                if directory:
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    stream = archive.open(member) if kind == "zip" else archive.extractfile(member)
                    if stream is None:
                        raise RuntimeError("Archive member has no readable data.")
                    with stream, target.open("xb") as output:
                        copy_cancelable(stream, output, check)
        check()
        if os.path.lexists(destination):
            raise FileExistsError(f"Destination appeared during extraction: {destination}")
        stage.rename(destination)


def safe_extract_zip(archive_path: Path, destination: Path, check_cancelled: Callable[[], None] = lambda: None) -> None:
    _extract(archive_path, destination, "zip", check_cancelled)


def safe_extract_tar(archive_path: Path, destination: Path, check_cancelled: Callable[[], None] = lambda: None) -> None:
    _extract(archive_path, destination, "tar", check_cancelled)


def create_archive(inputs: list[Path], output: Path, kind: str, check: Callable[[], None] = lambda: None, level: int = 6) -> Path:
    previous = file_identity(output)
    files: list[tuple[Path, str]] = []
    names: set[str] = set()
    for entry in inputs:
        check()
        if entry.is_symlink():
            raise ValueError(f"Archive creation does not follow symbolic links: {entry}")
        if entry.resolve() == output.resolve():
            raise ValueError("An archive cannot replace its own input.")
        for child in ([entry] if entry.is_file() else sorted(entry.rglob("*"))):
            check()
            if child.is_symlink():
                raise ValueError(f"Archive creation does not follow symbolic links: {child}")
            if not child.is_file() or child.resolve() == output.resolve():
                continue
            name = child.name if child == entry else (Path(entry.name) / child.relative_to(entry)).as_posix()
            if os.path.normcase(name) in names:
                raise ValueError(f"Duplicate archive member name: {name}")
            names.add(os.path.normcase(name))
            files.append((child, name))
    modes = {"tar": "w", "tar.gz": "w:gz", "tar.bz2": "w:bz2", "tar.xz": "w:xz"}
    if kind != "zip" and kind not in modes:
        raise ValueError(f"Unsupported archive format: {kind}")
    with tempfile.TemporaryDirectory(prefix=".foundry-archive-", dir=output.parent) as raw_stage:
        staged = Path(raw_stage) / "archive"
        if kind == "zip":
            with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level) as archive:
                for child, name in files:
                    info = zipfile.ZipInfo.from_file(child, arcname=name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info._compresslevel = level  # Python 3.11/3.12 streaming ZipInfo API.
                    with child.open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
                        copy_cancelable(source, target, check)
        else:
            with tarfile.open(staged, modes[kind]) as archive:
                for child, name in files:
                    check()
                    with child.open("rb") as source:
                        class CheckedReader:
                            def read(self, size: int = -1) -> bytes:
                                check()
                                return source.read(size)
                        archive.addfile(archive.gettarinfo(str(child), arcname=name), CheckedReader())
        check()
        commit_output(staged, output, previous)
    return output

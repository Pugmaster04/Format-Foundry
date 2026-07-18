from __future__ import annotations

import shutil
import stat
import tarfile
import zipfile
from pathlib import Path


MAX_ARCHIVE_MEMBERS = 500_000


def _safe_member_target(destination: Path, member_name: str) -> Path:
    destination_root = destination.resolve()
    target = (destination_root / member_name).resolve()
    try:
        target.relative_to(destination_root)
    except ValueError as exc:
        raise RuntimeError(f"Archive member escapes the destination: {member_name}") from exc
    return target


def _ensure_archive_fits(destination: Path, total_size: int) -> None:
    free_bytes = shutil.disk_usage(destination).free
    if total_size > free_bytes:
        raise RuntimeError(
            "Archive contents exceed the free space available in the destination "
            f"({total_size} bytes required, {free_bytes} bytes available)."
        )


def safe_extract_zip(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise RuntimeError(f"Archive contains too many entries ({len(members):,}).")

        total_size = 0
        for member in members:
            _safe_member_target(destination, member.filename)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"Symbolic links are not allowed in ZIP archives: {member.filename}")
            total_size += max(0, int(member.file_size))

        _ensure_archive_fits(destination, total_size)
        archive.extractall(destination)


def safe_extract_tar(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise RuntimeError(f"Archive contains too many entries ({len(members):,}).")

        total_size = 0
        for member in members:
            _safe_member_target(destination, member.name)
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise RuntimeError(f"Links and special files are not allowed in TAR archives: {member.name}")
            total_size += max(0, int(member.size))

        _ensure_archive_fits(destination, total_size)
        archive.extractall(destination, members=members, filter="data")

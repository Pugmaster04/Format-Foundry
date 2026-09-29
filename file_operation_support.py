"""Conservative file commits shared by destructive desktop operations."""

from __future__ import annotations

import os
from pathlib import Path


def path_key(path: Path) -> str:
    return os.path.normcase(str(path.absolute()))


def available_path(path: Path, reserved: set[str] | None = None) -> Path:
    reserved = reserved or set()
    candidate = path
    index = 1
    while os.path.lexists(candidate) or path_key(candidate) in reserved:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        index += 1
    return candidate


def plan_renames(rows: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    reserved: set[str] = set()
    result = []
    sources = [path_key(source) for source, _ in rows]
    if len(set(sources)) != len(sources):
        raise ValueError("A file is listed more than once in the rename batch.")
    for source, target in rows:
        if source.parent != target.parent:
            raise ValueError("Rename targets must stay in the source directory.")
        if path_key(source) != path_key(target):
            target = available_path(target, reserved)
        reserved.add(path_key(target))
        result.append((source, target))
    return result


def apply_renames(rows: list[tuple[Path, Path]]) -> int:
    changes = [(s, t) for s, t in rows if path_key(s) != path_key(t)]
    keys = [path_key(t) for _, t in changes]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate rename destinations; rebuild the preview.")
    for source, target in changes:
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Only regular files can be renamed: {source}")
        if os.path.lexists(target):
            raise FileExistsError(f"Destination changed; rebuild the preview: {target}")
    linked: list[tuple[Path, Path]] = []
    removed: list[tuple[Path, Path]] = []
    try:
        # Exclusive hard links cannot clobber a destination created after preview.
        # All originals remain intact until every destination has been reserved.
        for source, target in changes:
            os.link(source, target, follow_symlinks=False)
            linked.append((source, target))
        for source, target in changes:
            if not os.path.samefile(source, target):
                raise OSError(f"Source changed during rename; original retained at {target}")
            source.unlink()
            removed.append((source, target))
    except OSError:
        for source, target in reversed(removed):
            if not os.path.lexists(source):
                os.link(target, source, follow_symlinks=False)
        for source, target in reversed(linked):
            if source.exists() and target.exists() and os.path.samefile(source, target):
                target.unlink()
        raise
    return len(changes)


def file_identity(path: Path) -> tuple[int, int, int, int] | None:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Output is not a regular file: {path}")
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def commit_output(staged: Path, target: Path, previous: tuple[int, int, int, int] | None) -> None:
    if file_identity(target) != previous:
        raise FileExistsError(f"Output changed while processing; original kept: {target}")
    if previous is None:
        os.link(staged, target, follow_symlinks=False)
        staged.unlink()
    else:
        os.replace(staged, target)

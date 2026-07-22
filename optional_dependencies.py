"""Lazy access to optional libraries used by specialized workflows."""

from __future__ import annotations

import importlib
import importlib.util
from functools import cache, lru_cache
from types import ModuleType
from typing import Any


def dependency_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


@cache
def optional_module(module_name: str) -> ModuleType | None:
    try:
        return importlib.import_module(module_name)
    except (ImportError, OSError):
        return None


def yaml_module() -> ModuleType | None:
    return optional_module("yaml")


def imageio_ffmpeg_module() -> ModuleType | None:
    return optional_module("imageio_ffmpeg")


def windnd_module() -> ModuleType | None:
    return optional_module("windnd")


@lru_cache(maxsize=1)
def torrent_class() -> Any | None:
    module = optional_module("torrentool.api")
    return getattr(module, "Torrent", None) if module else None

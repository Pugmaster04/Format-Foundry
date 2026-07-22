"""Versioned, recoverable JSON settings storage."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from support_runtime import atomic_write_json

SETTINGS_SCHEMA_KEY = "settings_schema_version"
CURRENT_SETTINGS_SCHEMA_VERSION = 1
Migration = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class SettingsLoadResult:
    data: dict[str, Any]
    notice: str = ""
    migrated: bool = False
    recovery_path: Path | None = None
    read_only: bool = False


def _recovery_copy(path: Path, reason: str) -> Path | None:
    if not path.is_file():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    recovery_path = path.with_name(f"{path.stem}.{reason}.{stamp}{path.suffix}")
    try:
        shutil.copy2(path, recovery_path)
    except OSError:
        return None
    return recovery_path


def migrate_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    legacy_names = {
        "show_overview": "show_overview_panel",
        "borderless": "borderless_maximized",
        "reduce_animations": "reduce_motion",
    }
    for old_name, new_name in legacy_names.items():
        if old_name in migrated and new_name not in migrated:
            migrated[new_name] = migrated.pop(old_name)
    migrated[SETTINGS_SCHEMA_KEY] = 1
    return migrated


DEFAULT_MIGRATIONS: Mapping[int, Migration] = {0: migrate_v0_to_v1}


def load_settings_document(
    path: Path,
    defaults: Mapping[str, Any],
    *,
    schema_version: int = CURRENT_SETTINGS_SCHEMA_VERSION,
    migrations: Mapping[int, Migration] = DEFAULT_MIGRATIONS,
) -> SettingsLoadResult:
    merged_defaults = dict(defaults)
    merged_defaults[SETTINGS_SCHEMA_KEY] = schema_version
    if not path.exists():
        return SettingsLoadResult(merged_defaults)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("settings root is not a JSON object")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        recovery_path = _recovery_copy(path, "corrupt")
        notice = f"Settings were reset because {path.name} could not be read: {exc}."
        if recovery_path:
            notice += f" A recovery copy was preserved as {recovery_path.name}."
        return SettingsLoadResult(merged_defaults, notice=notice, recovery_path=recovery_path)

    raw_version = payload.get(SETTINGS_SCHEMA_KEY, 0)
    try:
        source_version = int(raw_version)
    except (TypeError, ValueError):
        source_version = 0
    if source_version > schema_version:
        recovery_path = _recovery_copy(path, "future")
        notice = (
            f"Settings from schema {source_version} are newer than this app supports; "
            "known values were loaded without overwriting the original file."
        )
        merged = dict(merged_defaults)
        merged.update({key: value for key, value in payload.items() if key in merged_defaults})
        merged[SETTINGS_SCHEMA_KEY] = schema_version
        return SettingsLoadResult(merged, notice=notice, recovery_path=recovery_path, read_only=True)

    migrated = False
    while source_version < schema_version:
        migration = migrations.get(source_version)
        if migration is None:
            recovery_path = _recovery_copy(path, "unmigrated")
            notice = f"No settings migration exists from schema {source_version}; defaults were restored."
            return SettingsLoadResult(merged_defaults, notice=notice, recovery_path=recovery_path)
        payload = migration(payload)
        source_version += 1
        migrated = True

    merged = dict(merged_defaults)
    merged.update(payload)
    merged[SETTINGS_SCHEMA_KEY] = schema_version
    if migrated:
        atomic_write_json(path, merged)
    return SettingsLoadResult(merged, migrated=migrated)


def save_settings_document(path: Path, data: Mapping[str, Any], *, schema_version: int = CURRENT_SETTINGS_SCHEMA_VERSION) -> None:
    payload = dict(data)
    payload[SETTINGS_SCHEMA_KEY] = schema_version
    atomic_write_json(path, payload)

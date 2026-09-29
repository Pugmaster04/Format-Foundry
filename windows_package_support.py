"""Windows package identity and Store lifecycle support for the frozen app."""

from __future__ import annotations

import ctypes
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app_identity import LEGACY_PRODUCT_SLUGS, PRODUCT_SLUG

STORE_UPDATES_URI = "ms-windows-store://downloadsandupdates"
WINDOWS_UNINSTALL_URI = "ms-settings:appsfeatures"


@dataclass(frozen=True)
class WindowsPackage:
    family_name: str
    full_name: str
    install_path: Path
    channel: str = "development"
    store_product_id: str = ""

    @property
    def store_uri(self) -> str:
        if re.fullmatch(r"[A-Za-z0-9]{12}", self.store_product_id):
            return f"ms-windows-store://pdp/?ProductId={self.store_product_id}"
        return STORE_UPDATES_URI


def _read_package_string(api: Any) -> str | None:
    api.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_wchar_p]
    api.restype = ctypes.c_long
    length = ctypes.c_uint32(0)
    if api(ctypes.byref(length), None) != 122 or not 0 < length.value < 32768:
        return None
    buffer = ctypes.create_unicode_buffer(length.value)
    if api(ctypes.byref(length), buffer) != 0:
        return None
    return str(buffer.value) or None


def current_package_identity() -> WindowsPackage | None:
    if os.name != "nt":
        return None
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        family = _read_package_string(kernel.GetCurrentPackageFamilyName)
        full_name = _read_package_string(kernel.GetCurrentPackageFullName)
        install_path = _read_package_string(kernel.GetCurrentPackagePath)
    except (AttributeError, OSError):
        return None
    if not family or not full_name or not install_path:
        return None
    return WindowsPackage(family, full_name, Path(install_path))


@lru_cache(maxsize=1)
def format_foundry_package() -> WindowsPackage | None:
    # A source run using a Store-installed Python interpreter is not our MSIX app.
    if not getattr(sys, "frozen", False):
        return None
    identity = current_package_identity()
    if identity is None:
        return None
    executable = Path(sys.executable)
    if executable.stem not in {PRODUCT_SLUG, f"{PRODUCT_SLUG}_Updater"}:
        return None
    try:
        metadata_path = identity.install_path / "App" / "msix-distribution.json"
        if metadata_path.stat().st_size > 16384:
            return identity
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("product_slug") != PRODUCT_SLUG:
            return identity
        package_name = identity.family_name.rsplit("_", 1)[0]
        if metadata.get("package_name") != package_name:
            return identity
        product_id = str(metadata.get("store_product_id", ""))
        return WindowsPackage(
            identity.family_name, identity.full_name, identity.install_path,
            channel=str(metadata.get("channel", "development")),
            store_product_id=product_id if re.fullmatch(r"[A-Za-z0-9]{12}", product_id) else "",
        )
    except (OSError, ValueError):
        # Missing metadata must not let a packaged app install an EXE over itself.
        return identity


def windows_local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")


def packaged_settings_root() -> Path | None:
    package = format_foundry_package()
    if package is None:
        return None
    return windows_local_appdata() / "Packages" / package.family_name / "LocalState"


def migrate_legacy_settings(root: Path, settings_filename: str) -> None:
    """Copy a missing settings document; never move or modify the EXE's data."""
    if root != packaged_settings_root():
        return
    destination = root / PRODUCT_SLUG / settings_filename
    if destination.exists():
        return
    for slug in (PRODUCT_SLUG, *LEGACY_PRODUCT_SLUGS):
        source = windows_local_appdata() / slug / settings_filename
        try:
            if source.is_file() and source.stat().st_size <= 1024 * 1024:
                data = source.read_bytes()
                if len(data) > 1024 * 1024:
                    return
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary_path = None
                try:
                    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as target:
                        temporary_path = Path(target.name)
                        target.write(data)
                        target.flush()
                        os.fsync(target.fileno())
                    # Linking the finished file preserves any concurrently saved settings.
                    os.link(temporary_path, destination)
                finally:
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)
                return
        except FileExistsError:
            return
        except OSError:
            return


def open_store_updates() -> None:
    os.startfile(STORE_UPDATES_URI)


def open_store_listing() -> None:
    package = format_foundry_package()
    os.startfile(package.store_uri if package else STORE_UPDATES_URI)


def package_runtime_report() -> dict[str, str]:
    package = format_foundry_package()
    if package is None:
        return {"channel": "unpackaged"}
    return {
        "channel": package.channel,
        "package_family": package.family_name,
        "package_full_name": package.full_name,
        "app_updates": "microsoft-store",
        "uninstall": "windows-settings",
    }

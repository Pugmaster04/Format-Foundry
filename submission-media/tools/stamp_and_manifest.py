"""Stamp Format Foundry PNG metadata and produce a hash manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, PngImagePlugin

MEDIA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MEDIA_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from format_foundry_provenance import (  # noqa: E402
    ORIGIN_REPOSITORY,
    PROJECT_OWNER,
    PROJECT_PROVENANCE_ID,
    canonical_identity,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_media_path(relative_path: str) -> Path:
    candidate = (MEDIA_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise ValueError(f"Media path escapes the kit directory: {relative_path}") from exc
    return candidate


def stamp_png(path: Path, *, title: str, description: str) -> tuple[int, int]:
    if path.suffix.lower() != ".png":
        raise ValueError(f"Only PNG metadata stamping is supported: {path}")
    temporary = path.with_name(f".{path.stem}.stamp.tmp.png")
    with Image.open(path) as opened:
        opened.load()
        image = opened.copy()
        width, height = image.size
        metadata = PngImagePlugin.PngInfo()
        for key, value in opened.info.items():
            if isinstance(key, str) and isinstance(value, str):
                metadata.add_text(key, value)
        metadata.add_text("Title", title)
        metadata.add_text("Description", description)
        metadata.add_text("Author", PROJECT_OWNER)
        metadata.add_text("Copyright", "Copyright (c) 2026 Pugmaster04. All rights reserved.")
        metadata.add_text("Project", "Format Foundry")
        metadata.add_text("Origin", ORIGIN_REPOSITORY)
        metadata.add_text("Provenance-ID", PROJECT_PROVENANCE_ID)
        metadata.add_text("Software", "Format Foundry submission media pipeline")
        save_options: dict[str, Any] = {"format": "PNG", "pnginfo": metadata, "optimize": True}
        if "dpi" in opened.info:
            save_options["dpi"] = opened.info["dpi"]
        if "icc_profile" in opened.info:
            save_options["icc_profile"] = opened.info["icc_profile"]
        image.save(temporary, **save_options)
    os.replace(temporary, path)
    return width, height


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=MEDIA_ROOT / "media-catalog.json")
    parser.add_argument("--manifest", type=Path, default=MEDIA_ROOT / "MEDIA_MANIFEST.json")
    args = parser.parse_args(argv)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog.get("provenance_id") != PROJECT_PROVENANCE_ID:
        raise ValueError("Media catalog provenance ID does not match Format Foundry.")
    generated_at_utc = str(catalog.get("generated_at_utc", "")).strip()
    if not generated_at_utc.endswith("Z"):
        raise ValueError("Media catalog generated_at_utc must be an explicit UTC timestamp ending in Z.")
    try:
        parsed_timestamp = datetime.fromisoformat(generated_at_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Media catalog generated_at_utc is not a valid ISO-8601 timestamp.") from exc
    utc_offset = parsed_timestamp.utcoffset()
    if utc_offset is None or utc_offset.total_seconds() != 0:
        raise ValueError("Media catalog generated_at_utc must use UTC.")

    records: list[dict[str, Any]] = []
    for entry in catalog.get("assets", []):
        path = safe_media_path(str(entry["path"]))
        if not path.is_file():
            raise FileNotFoundError(path)
        width, height = stamp_png(path, title=str(entry["role"]), description=str(entry["caption"]))
        records.append(
            {
                **entry,
                "width": width,
                "height": height,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema": "format-foundry/media-manifest/v1",
        "generated_at_utc": generated_at_utc,
        "identity": canonical_identity(),
        "assets": records,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Stamped and indexed {len(records)} PNG files: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

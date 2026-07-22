"""Build a deterministic, integrity-checked Devpost media archive."""

from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path

MEDIA_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "Format-Foundry-Devpost-Media-Kit.zip"
ARCHIVE_PATH = MEDIA_ROOT / ARCHIVE_NAME
CHECKSUM_PATH = MEDIA_ROOT / f"{ARCHIVE_NAME}.sha256"
FIXED_ZIP_TIME = (2026, 7, 13, 16, 0, 0)
ROOT_FILES = (
    "README.md",
    "VIDEO_STORYBOARD.md",
    "MEDIA_MANIFEST.json",
    "media-catalog.json",
    "render.html",
    "media.css",
    "render.js",
    "render_media.ps1",
)


def archive_sources() -> list[Path]:
    paths = [MEDIA_ROOT / name for name in ROOT_FILES]
    for pattern in ("exports/*.png", "screenshots/*.png", "tools/*.py"):
        paths.extend(MEDIA_ROOT.glob(pattern))
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Media archive input is missing: {missing[0]}")
    return sorted(set(paths), key=lambda path: path.relative_to(MEDIA_ROOT).as_posix())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    temporary = ARCHIVE_PATH.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in archive_sources():
                relative = source.relative_to(MEDIA_ROOT).as_posix()
                info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temporary, ARCHIVE_PATH)
    finally:
        temporary.unlink(missing_ok=True)

    digest = sha256_file(ARCHIVE_PATH)
    CHECKSUM_PATH.write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="ascii")
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"Media archive integrity failed at {bad_member}")
        entry_count = len(archive.infolist())
    print(f"Packaged {entry_count} media-kit files: {ARCHIVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

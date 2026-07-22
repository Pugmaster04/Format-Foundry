"""Generate a hash-bound release provenance manifest for official artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from format_foundry_provenance import ORIGIN_REPOSITORY, canonical_identity  # noqa: E402


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_source_commit() -> str:
    environment_sha = os.environ.get("GITHUB_SHA", "").strip()
    if environment_sha:
        return environment_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def artifact_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"Release artifact is not a file: {path}")
    return {
        "filename": resolved.name,
        "bytes": resolved.stat().st_size,
        "sha256": hash_file(resolved),
    }


def build_manifest(*, version: str, source_commit: str, artifacts: list[Path]) -> dict[str, Any]:
    records = sorted((artifact_record(path) for path in artifacts), key=lambda item: item["filename"].lower())
    names = [record["filename"] for record in records]
    if len(names) != len(set(names)):
        raise ValueError("Release artifact filenames must be unique in the provenance manifest.")

    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    run_url = ""
    if run_id:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        repository = os.environ.get("GITHUB_REPOSITORY", "Pugmaster04/Format-Foundry")
        run_url = f"{server}/{repository}/actions/runs/{run_id}"

    return {
        "schema": "format-foundry/release-provenance/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "identity": canonical_identity(),
        "release": {
            "version": version,
            "source_commit": source_commit,
            "source_repository": ORIGIN_REPOSITORY,
            "workflow_run": run_url,
        },
        "artifacts": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release package version")
    parser.add_argument("--source-commit", default="", help="Source commit SHA; auto-detected when omitted")
    parser.add_argument("--artifact", action="append", default=[], help="Artifact path; repeat for each file")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON manifest")
    args = parser.parse_args(argv)

    if not args.artifact:
        parser.error("at least one --artifact is required")
    source_commit = args.source_commit.strip() or detect_source_commit()
    manifest = build_manifest(
        version=args.version.strip(),
        source_commit=source_commit,
        artifacts=[Path(value) for value in args.artifact],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote provenance for {len(manifest['artifacts'])} artifacts: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

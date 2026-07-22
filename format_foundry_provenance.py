"""Canonical, privacy-preserving provenance identity for Format Foundry."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path
from typing import Any


PROVENANCE_SCHEMA = "format-foundry/provenance/v1"
PROJECT_NAME = "Format Foundry"
PROJECT_ID = "io.github.pugmaster04.format-foundry"
PROJECT_OWNER = "Pugmaster04"
ORIGIN_REPOSITORY = "https://github.com/Pugmaster04/Format-Foundry"
PROJECT_PROVENANCE_ID = "ffp1-af300b981ec8a9a505ca56a575193ed8a896f1f4b924019d2e8219290f598bee"


class ProvenanceError(RuntimeError):
    """Raised when bundled project identity data does not match the app."""


def _canonical_identity_text() -> str:
    return "\n".join((PROVENANCE_SCHEMA, PROJECT_ID, PROJECT_OWNER, ORIGIN_REPOSITORY))


def calculate_project_provenance_id() -> str:
    digest = hashlib.sha256(_canonical_identity_text().encode("utf-8")).hexdigest()
    return f"ffp1-{digest}"


def verify_project_identity() -> None:
    calculated = calculate_project_provenance_id()
    if not hmac.compare_digest(calculated, PROJECT_PROVENANCE_ID):
        raise ProvenanceError("Format Foundry's canonical project identity does not match its provenance ID.")


def canonical_identity() -> dict[str, Any]:
    verify_project_identity()
    return {
        "schema": PROVENANCE_SCHEMA,
        "project_name": PROJECT_NAME,
        "project_id": PROJECT_ID,
        "project_owner": PROJECT_OWNER,
        "provenance_id": PROJECT_PROVENANCE_ID,
        "origin_repository": ORIGIN_REPOSITORY,
        "copyright": "Copyright (c) 2026 Pugmaster04. All rights reserved.",
        "license": "Proprietary; see LICENSE in the official repository.",
        "verification_command": "gh attestation verify <artifact> -R Pugmaster04/Format-Foundry",
    }


def _identity_candidates() -> tuple[Path, ...]:
    source_root = Path(__file__).resolve().parent
    resource_root = Path(getattr(sys, "_MEIPASS", source_root))
    return (
        resource_root / "provenance" / "project-identity.json",
        source_root / "packaging" / "provenance" / "project-identity.json",
        Path(sys.executable).resolve().parent / "provenance" / "project-identity.json",
    )


def _validate_identity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    canonical = canonical_identity()
    stable_keys = (
        "schema",
        "project_name",
        "project_id",
        "project_owner",
        "provenance_id",
        "origin_repository",
    )
    mismatches = [key for key in stable_keys if payload.get(key) != canonical[key]]
    if mismatches:
        raise ProvenanceError(f"Bundled provenance identity mismatch: {', '.join(mismatches)}")
    return payload


def load_embedded_identity() -> dict[str, Any]:
    for candidate in _identity_candidates():
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProvenanceError(f"Unable to read bundled provenance identity: {candidate}") from exc
        if not isinstance(payload, dict):
            raise ProvenanceError("Bundled provenance identity must be a JSON object.")
        return _validate_identity_payload(payload)
    return canonical_identity()


def build_runtime_provenance(*, component: str, version: str) -> dict[str, Any]:
    return {
        "identity": load_embedded_identity(),
        "component": component,
        "version": version,
        "distribution": "frozen" if getattr(sys, "frozen", False) else "source",
    }


def runtime_provenance_json(*, component: str, version: str) -> str:
    return json.dumps(build_runtime_provenance(component=component, version=version), indent=2, sort_keys=True)

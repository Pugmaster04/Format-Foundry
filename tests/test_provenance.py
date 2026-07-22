import json
import tempfile
import unittest
from pathlib import Path

import format_foundry_provenance as provenance
from tools.generate_provenance_manifest import build_manifest, hash_file

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceTests(unittest.TestCase):
    def test_canonical_fingerprint_is_stable(self) -> None:
        provenance.verify_project_identity()
        self.assertEqual(
            provenance.calculate_project_provenance_id(),
            "ffp1-af300b981ec8a9a505ca56a575193ed8a896f1f4b924019d2e8219290f598bee",
        )

    def test_bundled_identity_matches_python_identity(self) -> None:
        payload = json.loads(
            (ROOT / "packaging/provenance/project-identity.json").read_text(encoding="utf-8")
        )
        canonical = provenance.canonical_identity()
        for key in (
            "schema",
            "project_name",
            "project_id",
            "project_owner",
            "provenance_id",
            "origin_repository",
        ):
            self.assertEqual(payload[key], canonical[key])

    def test_specs_bundle_the_identity_record(self) -> None:
        for spec_name in ("FormatFoundry.spec", "FormatFoundry_Updater.spec"):
            source = (ROOT / spec_name).read_text(encoding="utf-8")
            self.assertIn("packaging/provenance/project-identity.json", source)
            self.assertIn("'provenance'", source)

    def test_release_manifest_binds_artifact_hash_and_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "FormatFoundry_test.exe"
            artifact.write_bytes(b"official-format-foundry-test-artifact")
            manifest = build_manifest(
                version="0.5.0-beta",
                source_commit="a" * 40,
                artifacts=[artifact],
            )

            self.assertEqual(manifest["identity"]["provenance_id"], provenance.PROJECT_PROVENANCE_ID)
            self.assertEqual(manifest["release"]["source_commit"], "a" * 40)
            self.assertEqual(manifest["artifacts"][0]["sha256"], hash_file(artifact))


if __name__ == "__main__":
    unittest.main()

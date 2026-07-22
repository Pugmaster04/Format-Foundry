import json
import tempfile
import unittest
from pathlib import Path

from tools import hackathon_audit


class HackathonAuditTests(unittest.TestCase):
    def test_events_form_a_verified_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            first = hackathon_audit.append_event(
                category="implementation",
                summary="Added a tested feature",
                evidence=["tests/example"],
                log_path=log_path,
            )
            second = hackathon_audit.append_event(
                category="verification",
                summary="Verification passed",
                verification=["1 test passed"],
                log_path=log_path,
            )
            result = hackathon_audit.verify_events(log_path)

            self.assertEqual(result["event_count"], 2)
            self.assertEqual(second["previous_hash"], first["event_hash"])
            self.assertEqual(result["head_hash"], second["event_hash"])

    def test_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            hackathon_audit.append_event(
                category="media",
                summary="Created submission image",
                log_path=log_path,
            )
            event = json.loads(log_path.read_text(encoding="utf-8"))
            event["summary"] = "Altered after the fact"
            log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

            with self.assertRaises(hackathon_audit.AuditError):
                hackathon_audit.verify_events(log_path)

    def test_secret_like_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            synthetic_secret = "sk-" + "examplecredentialvalue123456789"
            with self.assertRaises(hackathon_audit.AuditError):
                hackathon_audit.append_event(
                    category="configuration",
                    summary=f"Used {synthetic_secret}",
                    log_path=log_path,
                )
            self.assertFalse(log_path.exists())


if __name__ == "__main__":
    unittest.main()

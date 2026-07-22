# OpenAI Build Week Audit Trail

This directory distinguishes Format Foundry work completed during the OpenAI Build Week submission
period from the pre-existing project. The official submission period runs from July 13, 2026 at
9:00 AM Pacific Time through July 21, 2026 at 5:00 PM Pacific Time.

## Files

- `HACKATHON_WEEK_AUDIT.md` is the human-readable evidence and compliance report.
- `events.jsonl` is an append-only ledger. Every event contains the previous event hash and its own
  SHA-256 hash, so edits, reordering, and missing entries are detectable.
- `AUDIT_SNAPSHOT.json` records the ledger head, Git state, and hashes of important evidence files.

## Commands

Verify the complete chain:

```text
python tools/hackathon_audit.py verify
```

Append an event:

```text
python tools/hackathon_audit.py append --category verification --summary "Windows smoke test passed" --evidence "build report path"
```

Regenerate the evidence snapshot:

```text
python tools/hackathon_audit.py snapshot --evidence submission-media/MEDIA_MANIFEST.json
```

## Evidence policy

- Record only work and tool usage that actually occurred.
- Never place API keys, access tokens, private keys, credentials, private task transcripts, or
  personal filesystem paths in the ledger.
- A Codex Session ID should be added only after obtaining it through the required `/feedback` flow.
- GPT-5.6 usage should identify a real contribution and resulting artifact. It must not be inferred
  from a filename, conversation summary, or model assumption.
- The official rules and Devpost website remain the source of truth.

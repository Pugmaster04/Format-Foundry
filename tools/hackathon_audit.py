"""Maintain a privacy-safe, hash-chained OpenAI Build Week audit ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "hackathon-audit" / "events.jsonl"
DEFAULT_SNAPSHOT = ROOT / "hackathon-audit" / "AUDIT_SNAPSHOT.json"
GENESIS_HASH = "0" * 64
EVENT_SCHEMA = "format-foundry/hackathon-audit-event/v1"

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class AuditError(RuntimeError):
    """Raised when the audit ledger is invalid or unsafe to update."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_event_bytes(event: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in event.items() if key != "event_hash"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def calculate_event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_event_bytes(event)).hexdigest()


def load_events(log_path: Path = DEFAULT_LOG) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditError(f"Invalid JSON on audit line {line_number}.") from exc
        if not isinstance(event, dict):
            raise AuditError(f"Audit line {line_number} is not a JSON object.")
        events.append(event)
    return events


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def verify_events(log_path: Path = DEFAULT_LOG) -> dict[str, Any]:
    events = load_events(log_path)
    previous_hash = GENESIS_HASH
    for index, event in enumerate(events, start=1):
        if event.get("schema") != EVENT_SCHEMA:
            raise AuditError(f"Event {index} has an unsupported schema.")
        if event.get("sequence") != index:
            raise AuditError(f"Event {index} has an invalid sequence number.")
        if event.get("previous_hash") != previous_hash:
            raise AuditError(f"Event {index} does not link to the previous event.")
        expected_hash = calculate_event_hash(event)
        if event.get("event_hash") != expected_hash:
            raise AuditError(f"Event {index} hash does not match its contents.")
        previous_hash = expected_hash
    return {
        "ok": True,
        "event_count": len(events),
        "head_hash": previous_hash,
        "log": portable_path(log_path),
    }


def reject_secrets(values: Iterable[str]) -> None:
    for value in values:
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise AuditError("Potential credential or private key detected; audit entry was not written.")


def clean_list(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def append_event(
    *,
    category: str,
    summary: str,
    details: str = "",
    actor: str = "Pugmaster04 with Codex",
    evidence: Iterable[str] = (),
    tools: Iterable[str] = (),
    commands: Iterable[str] = (),
    verification: Iterable[str] = (),
    log_path: Path = DEFAULT_LOG,
) -> dict[str, Any]:
    category = category.strip()
    summary = summary.strip()
    details = details.strip()
    actor = actor.strip()
    if not category or not summary or not actor:
        raise AuditError("Category, summary, and actor are required.")

    normalized_evidence = clean_list(evidence)
    normalized_tools = clean_list(tools)
    normalized_commands = clean_list(commands)
    normalized_verification = clean_list(verification)
    reject_secrets(
        [category, summary, details, actor]
        + normalized_evidence
        + normalized_tools
        + normalized_commands
        + normalized_verification
    )

    chain = verify_events(log_path)
    event: dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "sequence": int(chain["event_count"]) + 1,
        "timestamp_utc": utc_now(),
        "actor": actor,
        "category": category,
        "summary": summary,
        "details": details,
        "tools": normalized_tools,
        "evidence": normalized_evidence,
        "commands": normalized_commands,
        "verification": normalized_verification,
        "previous_hash": str(chain["head_hash"]),
    }
    event["event_hash"] = calculate_event_hash(event)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=True) + "\n")
    return event


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_git_executable() -> str:
    """Return a directly executable Git binary without invoking a command shell."""
    candidates: list[str] = []
    configured = os.environ.get("GIT_EXECUTABLE", "").strip()
    if configured:
        candidates.append(configured)

    if os.name == "nt":
        discovered = shutil.which("git.exe")
        if discovered:
            candidates.append(discovered)
        for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
            program_files = os.environ.get(environment_name, "").strip()
            if program_files:
                candidates.extend(
                    [
                        str(Path(program_files) / "Git" / "cmd" / "git.exe"),
                        str(Path(program_files) / "Git" / "bin" / "git.exe"),
                    ]
                )
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            desktop_root = Path(local_app_data) / "GitHubDesktop"
            candidates.extend(
                str(path)
                for path in sorted(
                    desktop_root.glob("app-*/resources/app/git/cmd/git.exe"),
                    reverse=True,
                )
            )
    else:
        discovered = shutil.which("git")
        if discovered:
            candidates.append(discovered)

    for candidate in dict.fromkeys(candidates):
        path = Path(candidate).expanduser()
        if path.is_file() and (os.name != "nt" or path.suffix.lower() == ".exe"):
            return str(path)
    raise AuditError("Unable to locate an executable Git binary.")


def git_output(*args: str) -> str:
    try:
        result = subprocess.run(
            [resolve_git_executable(), *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditError(f"Unable to query git {' '.join(args)}.") from exc
    return result.stdout.strip()


def resolve_evidence_path(value: str) -> Path:
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise AuditError(f"Snapshot evidence must stay inside the repository: {value}") from exc
    if not candidate.is_file():
        raise AuditError(f"Snapshot evidence file does not exist: {value}")
    return candidate


def write_snapshot(
    *,
    evidence: Iterable[str],
    output_path: Path = DEFAULT_SNAPSHOT,
    log_path: Path = DEFAULT_LOG,
) -> dict[str, Any]:
    chain = verify_events(log_path)
    records = []
    for value in clean_list(evidence):
        path = resolve_evidence_path(value)
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    status_lines = [line for line in git_output("status", "--porcelain=v1").splitlines() if line]
    snapshot = {
        "schema": "format-foundry/hackathon-audit-snapshot/v1",
        "generated_at_utc": utc_now(),
        "event_period": {
            "submission_opens": "2026-07-13T16:00:00Z",
            "submission_closes": "2026-07-22T00:00:00Z",
            "source": "https://openai.devpost.com/rules",
        },
        "repository": {
            "origin": "https://github.com/Pugmaster04/Format-Foundry",
            "head_commit": git_output("rev-parse", "HEAD"),
            "branch": git_output("branch", "--show-current"),
            "working_tree_dirty": bool(status_lines),
            "working_tree_entries": status_lines,
        },
        "ledger": chain,
        "evidence_files": sorted(records, key=lambda item: item["path"].lower()),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="Audit JSONL path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    append_parser = subparsers.add_parser("append", help="Append one hash-chained audit event")
    append_parser.add_argument("--category", required=True)
    append_parser.add_argument("--summary", required=True)
    append_parser.add_argument("--details", default="")
    append_parser.add_argument("--actor", default="Pugmaster04 with Codex")
    append_parser.add_argument("--tool", action="append", default=[])
    append_parser.add_argument("--evidence", action="append", default=[])
    append_parser.add_argument("--command-run", action="append", default=[])
    append_parser.add_argument("--verification", action="append", default=[])

    subparsers.add_parser("verify", help="Verify sequence and every chained event hash")

    snapshot_parser = subparsers.add_parser("snapshot", help="Write a repository and evidence snapshot")
    snapshot_parser.add_argument("--output", type=Path, default=DEFAULT_SNAPSHOT)
    snapshot_parser.add_argument("--evidence", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = args.log.resolve()
    try:
        if args.command == "append":
            result = append_event(
                category=args.category,
                summary=args.summary,
                details=args.details,
                actor=args.actor,
                evidence=args.evidence,
                tools=args.tool,
                commands=args.command_run,
                verification=args.verification,
                log_path=log_path,
            )
        elif args.command == "verify":
            result = verify_events(log_path)
        else:
            result = write_snapshot(
                evidence=args.evidence,
                output_path=args.output.resolve(),
                log_path=log_path,
            )
    except AuditError as exc:
        parser.exit(1, f"audit error: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

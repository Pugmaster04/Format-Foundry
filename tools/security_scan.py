"""Scan tracked production Python and freezer specs, failing on actionable severity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "build" / "bandit.json")
    args = parser.parse_args()
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py", "*.spec"], cwd=ROOT,
    ).decode("utf-8").split("\0")
    targets = [name for name in names if name and not name.startswith(("tests/", "archive/"))]
    if not targets:
        raise RuntimeError("No tracked production Python files were found for security scanning.")
    args.report = args.report.resolve()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "bandit", "--ignore-nosec", "-f", "json", "-o", str(args.report), "--", *targets],
        cwd=ROOT, check=False,
    )
    if result.returncode not in {0, 1}:
        return result.returncode
    report = json.loads(args.report.read_text(encoding="utf-8"))
    findings = [item for item in report["results"] if item["issue_severity"] in {"MEDIUM", "HIGH"}]
    errors = report.get("errors", [])
    print(f"Scanned {len(targets)} production Python/spec files: {len(findings)} medium/high findings, {len(errors)} scan errors.")
    return 1 if findings or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

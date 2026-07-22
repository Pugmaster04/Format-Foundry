from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def timed_command(command: list[str], *, timeout: float) -> tuple[float, subprocess.CompletedProcess[str]]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return time.perf_counter() - started, completed


def record_limit(results: dict[str, Any], failures: list[str], name: str, value: float | int, limit: float | int) -> None:
    passed = value <= limit
    results[name] = {"value": value, "limit": limit, "passed": passed}
    if not passed:
        failures.append(f"{name}: {value} exceeded {limit}")


def measure_import(module_name: str, timeout: float = 30.0) -> float:
    elapsed, completed = timed_command([sys.executable, "-c", f"import {module_name}"], timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError(f"Import probe failed for {module_name}: {completed.stderr.strip()}")
    return elapsed


def measure_backend_detection(timeout: float = 30.0) -> float:
    code = "from backend_support import detect_backend_paths; detect_backend_paths()"
    elapsed, completed = timed_command([sys.executable, "-c", code], timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError(f"Backend detection probe failed: {completed.stderr.strip()}")
    return elapsed


def measure_frozen_smoke(path: Path, timeout: float) -> float:
    elapsed, completed = timed_command([str(path.resolve()), "--smoke-test"], timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError(f"Frozen smoke probe failed for {path}: {completed.stderr.strip() or completed.stdout.strip()}")
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce Format Foundry source, binary, and package performance budgets.")
    parser.add_argument("--budgets", type=Path, default=ROOT / "performance_budgets.json")
    parser.add_argument("--report", type=Path, default=ROOT / "build" / "performance-budget.json")
    parser.add_argument("--app-binary", type=Path)
    parser.add_argument("--updater-binary", type=Path)
    parser.add_argument("--installer", type=Path)
    args = parser.parse_args()

    budgets = json.loads(args.budgets.read_text(encoding="utf-8"))
    results: dict[str, Any] = {}
    failures: list[str] = []
    record_limit(
        results,
        failures,
        "source_main_import_seconds",
        round(measure_import("modular_file_utility_suite"), 4),
        float(budgets["source_main_import_seconds"]),
    )
    record_limit(
        results,
        failures,
        "source_updater_import_seconds",
        round(measure_import("suite_updater"), 4),
        float(budgets["source_updater_import_seconds"]),
    )
    record_limit(
        results,
        failures,
        "backend_detection_seconds",
        round(measure_backend_detection(), 4),
        float(budgets["backend_detection_seconds"]),
    )

    if args.app_binary:
        record_limit(
            results,
            failures,
            "frozen_app_smoke_seconds",
            round(measure_frozen_smoke(args.app_binary, float(budgets["frozen_app_smoke_seconds"]) + 10.0), 4),
            float(budgets["frozen_app_smoke_seconds"]),
        )
        record_limit(results, failures, "frozen_app_bytes", args.app_binary.stat().st_size, int(budgets["frozen_app_max_bytes"]))
    if args.updater_binary:
        record_limit(
            results,
            failures,
            "frozen_updater_smoke_seconds",
            round(measure_frozen_smoke(args.updater_binary, float(budgets["frozen_updater_smoke_seconds"]) + 10.0), 4),
            float(budgets["frozen_updater_smoke_seconds"]),
        )
        record_limit(
            results,
            failures,
            "frozen_updater_bytes",
            args.updater_binary.stat().st_size,
            int(budgets["frozen_updater_max_bytes"]),
        )
    if args.installer:
        record_limit(
            results,
            failures,
            "windows_installer_bytes",
            args.installer.stat().st_size,
            int(budgets["windows_installer_max_bytes"]),
        )

    payload = {"schema_version": 1, "passed": not failures, "results": results, "failures": failures}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

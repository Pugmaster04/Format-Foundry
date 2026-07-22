import argparse
import json
from pathlib import Path


REQUIRED_ROOT_FILES = [
    ".gitattributes",
    ".gitignore",
    "addons/__init__.py",
    "addons/idea_bank.py",
    "addons/pc_health.py",
    "addons/README.md",
    "build_linux.sh",
    "build_suite_release.bat",
    "build_windows.bat",
    "CHANGELOG.md",
    "accessibility_support.py",
    "app_identity.py",
    "docs/OPTIMIZATION_AUDIT.md",
    "FormatFoundry.spec",
    "FormatFoundry_Portable.spec",
    "FormatFoundry_Updater.spec",
    "format_foundry_provenance.py",
    "hackathon-audit/AUDIT_SNAPSHOT.json",
    "hackathon-audit/events.jsonl",
    "hackathon-audit/HACKATHON_WEEK_AUDIT.md",
    "hackathon-audit/README.md",
    "LINUX_PORT_AUDIT.md",
    "job_ledger.py",
    "modular_file_utility_suite.py",
    "optional_dependencies.py",
    "performance_budgets.json",
    "pyproject.toml",
    "PROJECT_PLAN.md",
    "README.md",
    "requirements-dev.txt",
    "requirements.txt",
    "settings_support.py",
    "suite_updater.py",
    "support_runtime.py",
    "packaging/provenance/project-identity.json",
    "THIRD_PARTY_NOTICES.txt",
    "tests/test_hackathon_audit.py",
    "tests/test_idea_bank.py",
    "tests/test_pc_health.py",
    "tools/hackathon_audit.py",
    "tools/performance_budget.py",
    "tools/ui_layout_probe.py",
    "update_manifest.example.json",
]


def find_missing_required_files(root: Path) -> list[str]:
    return [relative_path for relative_path in REQUIRED_ROOT_FILES if not (root / relative_path).exists()]


def build_report(root: Path) -> dict[str, object]:
    missing = find_missing_required_files(root)
    return {
        "root": str(root),
        "required_root_files": list(REQUIRED_ROOT_FILES),
        "missing_root_files": missing,
        "ok": not missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify that the repo contains the required root source files.")
    parser.add_argument("root", nargs="?", default=".", help="Repo root to verify")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = build_report(root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Repo root: {root}")
        if report["missing_root_files"]:
            print("Missing required root files:")
            for relative_path in report["missing_root_files"]:
                print(f"- {relative_path}")
        else:
            print("All required root files are present.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

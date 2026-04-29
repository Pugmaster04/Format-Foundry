import argparse
import json
from pathlib import Path


REQUIRED_ROOT_FILES = [
    ".gitattributes",
    ".gitignore",
    "build_linux.sh",
    "build_suite_release.bat",
    "build_windows.bat",
    "CHANGELOG.md",
    "FormatFoundry.spec",
    "FormatFoundry_Updater.spec",
    "LINUX_PORT_AUDIT.md",
    "modular_file_utility_suite.py",
    "PROJECT_PLAN.md",
    "README.md",
    "requirements.txt",
    "suite_updater.py",
    "support_runtime.py",
    "THIRD_PARTY_NOTICES.txt",
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

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from support_runtime import RELEASE_TRANSPORT_TAG, format_release_label, is_release_newer


LEGACY_ALPHA_FLOOR = "1.8.17"


def extract_constant(source: str, name: str) -> str:
    match = re.search(rf'^{re.escape(name)} = "([^"]+)"', source, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"{name} was not found in modular_file_utility_suite.py")
    return match.group(1)


def changelog_block(changelog: str, package_version: str) -> str:
    match = re.search(rf"^## \[{re.escape(package_version)}\] - .*$", changelog, flags=re.MULTILINE)
    if not match:
        return f"Release {format_release_label(package_version)}"
    lines = changelog[match.start() :].splitlines()
    block: list[str] = []
    for index, line in enumerate(lines):
        if index and line.startswith("## ["):
            break
        block.append(line)
    return "\n".join(block).strip()


def release_metadata(tag: str, app_source: str) -> dict[str, str]:
    package_version = extract_constant(app_source, "APP_VERSION")
    display_version = extract_constant(app_source, "APP_VERSION_LABEL")
    normalized_tag = tag.strip()
    if normalized_tag != RELEASE_TRANSPORT_TAG:
        raise RuntimeError(
            f"Beta migration releases must use transport tag {RELEASE_TRANSPORT_TAG}; received {normalized_tag or '(empty)'}."
        )
    if not is_release_newer(normalized_tag, LEGACY_ALPHA_FLOOR):
        raise RuntimeError(
            f"Transport tag {normalized_tag} must compare newer than legacy Alpha {LEGACY_ALPHA_FLOOR}."
        )
    return {
        "tag": normalized_tag,
        "package_version": package_version,
        "display_version": display_version,
        "title": f"Format Foundry {display_version}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and prepare the coordinated Format Foundry release contract.")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--changelog", default=str(ROOT / "CHANGELOG.md"))
    parser.add_argument("--notes", default=str(ROOT / "RELEASE_NOTES.md"))
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    app_source = (ROOT / "modular_file_utility_suite.py").read_text(encoding="utf-8", errors="replace")
    metadata = release_metadata(args.tag, app_source)
    changelog = Path(args.changelog).read_text(encoding="utf-8-sig", errors="replace")
    Path(args.notes).write_text(changelog_block(changelog, metadata["package_version"]) + "\n", encoding="utf-8")

    if args.github_output:
        output_path = Path(args.github_output)
        with output_path.open("a", encoding="utf-8", newline="\n") as handle:
            for key in ("tag", "package_version", "display_version", "title"):
                handle.write(f"{key}={metadata[key]}\n")
    else:
        for key, value in metadata.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

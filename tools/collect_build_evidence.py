"""Collect installed dependency notices and hash the frozen native payload.

This is a build inventory, not a legal compliance certification or a claim that
every build-environment dependency is shipped in the frozen program.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata as metadata
import json
import re
import sys
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def collect_notices(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    pending = []
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            requirement = Requirement(line)
            if requirement.marker is None or requirement.marker.evaluate():
                pending.append(requirement.name)
    seen: set[str] = set()
    inventory = []
    while pending:
        name = pending.pop()
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in seen:
            continue
        seen.add(key)
        distribution = metadata.distribution(name)
        notices = []
        for index, file in enumerate(distribution.files or []):
            if any(token in str(file).lower() for token in ("license", "copying", "notice")) and file.suffix.lower() not in {".py", ".pyc"}:
                source = Path(distribution.locate_file(file))
                if source.is_file() and source.stat().st_size < 4 * 1024 * 1024:
                    target = output / key / f"{index}-{file.name}"
                    target.parent.mkdir(exist_ok=True)
                    target.write_bytes(source.read_bytes())
                    notices.append(target.relative_to(output).as_posix())
        inventory.append({"name": distribution.metadata["Name"], "version": distribution.version,
                          "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License", ""),
                          "notices": notices, "scope": "requirement/build dependency; consult frozen payload inventory"})
        for dependency in distribution.requires or []:
            requirement = Requirement(dependency)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        (output / "Python-LICENSE.txt").write_bytes(python_license.read_bytes())
    (output / "THIRD_PARTY_NOTICES.txt").write_bytes((ROOT / "THIRD_PARTY_NOTICES.txt").read_bytes())
    (output / "dependencies.json").write_text(json.dumps(sorted(inventory, key=lambda d: d["name"]), indent=2) + "\n", encoding="utf-8")


def frozen_inventory(build: Path, output: Path) -> None:
    records = []
    for toc in sorted(build.glob("FormatFoundry*/Analysis-00.toc")):
        data = ast.literal_eval(toc.read_text(encoding="utf-8"))

        def visit(value: object, component: str = toc.parent.name) -> None:
            if not isinstance(value, (list, tuple)):
                return
            if len(value) == 3 and all(isinstance(item, str) for item in value):
                name, raw_source, kind = value
                if kind in {"BINARY", "EXTENSION"}:
                    source = Path(raw_source)
                    if source.is_file():
                        digest = hashlib.sha256()
                        with source.open("rb") as handle:
                            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                                digest.update(chunk)
                        records.append({"component": component, "path": name, "size": source.stat().st_size, "sha256": digest.hexdigest()})
            else:
                for item in value:
                    visit(item)

        visit(data)
    if not records:
        raise RuntimeError("No frozen native payload was found; build the application first.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"scope": "Frozen native binaries, not a license certification", "files": records}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notices", type=Path)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    if args.notices:
        collect_notices(args.notices)
    if args.frozen:
        frozen_inventory(ROOT / "build", args.frozen)

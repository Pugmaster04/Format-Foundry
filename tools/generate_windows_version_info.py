from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "modular_file_utility_suite.py"
OUTPUT_DIR = ROOT / "packaging" / "windows"


def read_versions() -> tuple[str, str]:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION = "([^"]+)"', source, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"APP_VERSION was not found in {SOURCE_PATH}")
    label_match = re.search(r'^APP_VERSION_LABEL = "([^"]+)"', source, flags=re.MULTILINE)
    return match.group(1), (label_match.group(1) if label_match else match.group(1))


def version_tuple(version: str) -> tuple[int, int, int, int]:
    numeric = [int(value) for value in re.findall(r"\d+", version)[:4]]
    numeric.extend([0] * (4 - len(numeric)))
    return tuple(numeric[:4])


def render_version_info(
    version: str,
    display_version: str,
    *,
    product_name: str,
    description: str,
    original_filename: str,
) -> str:
    numeric = version_tuple(version)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric},
    prodvers={numeric},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Format Foundry'),
          StringStruct('FileDescription', '{description}'),
          StringStruct('FileVersion', '{display_version}'),
          StringStruct('InternalName', '{Path(original_filename).stem}'),
          StringStruct('LegalCopyright', 'Copyright (c) Pugmaster04'),
          StringStruct('OriginalFilename', '{original_filename}'),
          StringStruct('ProductName', '{product_name}'),
          StringStruct('ProductVersion', '{display_version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    version, display_version = read_versions()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = {
        OUTPUT_DIR / "FormatFoundry_version_info.txt": {
            "product_name": "Format Foundry",
            "description": "Format Foundry desktop utility",
            "original_filename": "FormatFoundry.exe",
        },
        OUTPUT_DIR / "FormatFoundry_Updater_version_info.txt": {
            "product_name": "Format Foundry Updater",
            "description": "Format Foundry secure updater",
            "original_filename": "FormatFoundry_Updater.exe",
        },
    }
    for path, values in targets.items():
        path.write_text(render_version_info(version, display_version, **values), encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

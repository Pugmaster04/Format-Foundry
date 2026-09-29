"""Build and validate an unsigned Store submission or a Windows 11 test MSIX."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from PIL import Image

from app_identity import DISPLAY_VERSION, PACKAGE_VERSION, PRODUCT_NAME, PRODUCT_SLUG

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
UAP10 = "http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
RESCAP = "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
BLOCKMAP = "http://schemas.microsoft.com/appx/2010/blockmap"
UNSIGNED_OID = "OID.2.25.311729368913984317654407730594956997722=1"
IDENTITY_FIELDS = ("package_name", "publisher", "publisher_display_name", "store_product_id")
LOGOS = {"StoreLogo.png": 50, "Square44x44Logo.png": 44, "Square150x150Logo.png": 150}


def payload_source_hash() -> str:
    paths = set(ROOT.glob("*.py")) | set((ROOT / "addons").rglob("*.py"))
    paths.update(ROOT / name for name in (
        "FormatFoundry_MSIX.spec", "requirements.txt", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.txt",
        "assets/code_languages.json", "assets/universal_file_utility_suite.ico", "assets/universal_file_utility_suite_preview.png",
        "update_manifest.example.json", "packaging/provenance/project-identity.json",
        "packaging/windows/FormatFoundry_version_info.txt", "packaging/windows/FormatFoundry_Updater_version_info.txt",
    ))
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def msix_version(package_version: str, override: str = "") -> str:
    if override:
        if not re.fullmatch(r"\d+\.\d+\.\d+\.0", override):
            raise ValueError("Store version must have four numeric parts ending in .0.")
        parts = [int(part) for part in override.split(".")]
    else:
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-beta)?", package_version)
        if match is None:
            raise ValueError("Canonical version must be major.minor.patch, optionally ending in -beta.")
        major, minor, patch = map(int, match.groups())
        # The Store requires a nonzero major. The app keeps its canonical Beta label.
        parts = [major + 1, minor, patch, 0]
    if not 1 <= parts[0] <= 65535 or any(not 0 <= part <= 65535 for part in parts[1:]):
        raise ValueError("MSIX version parts must fit 16 bits and the major must be positive.")
    return ".".join(map(str, parts))


def package_identity(mode: str, data: dict[str, Any] | None = None) -> dict[str, str]:
    if mode == "candidate":
        return {
            "package_name": "FormatFoundry.Development",
            "publisher": f"CN=FormatFoundry Development, {UNSIGNED_OID}",
            "publisher_display_name": "Format Foundry Development",
            "store_product_id": "",
        }
    if mode != "store":
        raise ValueError("Mode must be candidate or store.")
    if data is not None and not isinstance(data, dict):
        raise ValueError("Store identity file must contain a JSON object.")
    result = {key: str((data or {}).get(key, "")).strip() for key in IDENTITY_FIELDS}
    if any(not value or "REPLACE" in value.upper() for value in result.values()):
        raise ValueError("Store mode requires all four real Partner Center product identity values.")
    if not re.fullmatch(r"[A-Za-z0-9.-]{3,50}", result["package_name"]):
        raise ValueError("Partner Center package name is invalid.")
    if not result["publisher"].startswith("CN=") or "OID." in result["publisher"]:
        raise ValueError("Use the exact Partner Center Publisher (CN=...), without the unsigned test OID.")
    if not re.fullmatch(r"[A-Za-z0-9]{12}", result["store_product_id"]):
        raise ValueError("Store product ID must be the 12-character value assigned by Partner Center.")
    return result


def manifest_bytes(identity: dict[str, str], version: str) -> bytes:
    for prefix, namespace in (("", FOUNDATION), ("uap", UAP), ("uap10", UAP10), ("rescap", RESCAP)):
        ET.register_namespace(prefix, namespace)
    root = ET.Element(f"{{{FOUNDATION}}}Package", {"IgnorableNamespaces": "uap uap10 rescap"})
    ET.SubElement(root, f"{{{FOUNDATION}}}Identity", {
        "Name": identity["package_name"], "Publisher": identity["publisher"],
        "Version": version, "ProcessorArchitecture": "x64",
    })
    properties = ET.SubElement(root, f"{{{FOUNDATION}}}Properties")
    for name, value in (
        ("DisplayName", PRODUCT_NAME), ("PublisherDisplayName", identity["publisher_display_name"]),
        ("Description", "File conversion, media, archives, checksums and optional download tools."),
        ("Logo", r"Assets\StoreLogo.png"),
    ):
        ET.SubElement(properties, f"{{{FOUNDATION}}}{name}").text = value
    resources = ET.SubElement(root, f"{{{FOUNDATION}}}Resources")
    ET.SubElement(resources, f"{{{FOUNDATION}}}Resource", {"Language": "en-US"})
    dependencies = ET.SubElement(root, f"{{{FOUNDATION}}}Dependencies")
    ET.SubElement(dependencies, f"{{{FOUNDATION}}}TargetDeviceFamily", {
        "Name": "Windows.Desktop", "MinVersion": "10.0.19041.0", "MaxVersionTested": "10.0.26100.0",
    })
    applications = ET.SubElement(root, f"{{{FOUNDATION}}}Applications")
    for app_id, executable, label, visibility in (
        ("FormatFoundry", r"App\FormatFoundry.exe", PRODUCT_NAME, "default"),
        ("BackendCenter", r"App\FormatFoundry_Updater.exe", f"{PRODUCT_NAME} Tools", "none"),
    ):
        application = ET.SubElement(applications, f"{{{FOUNDATION}}}Application", {
            "Id": app_id, "Executable": executable,
            f"{{{UAP10}}}RuntimeBehavior": "packagedClassicApp", f"{{{UAP10}}}TrustLevel": "mediumIL",
        })
        ET.SubElement(application, f"{{{UAP}}}VisualElements", {
            "DisplayName": label, "Description": "Convert, organize and inspect your files.",
            "Square150x150Logo": r"Assets\Square150x150Logo.png",
            "Square44x44Logo": r"Assets\Square44x44Logo.png", "BackgroundColor": "transparent",
            "AppListEntry": visibility,
        })
    capabilities = ET.SubElement(root, f"{{{FOUNDATION}}}Capabilities")
    ET.SubElement(capabilities, f"{{{RESCAP}}}Capability", {"Name": "runFullTrust"})
    ET.indent(root, space="  ")
    return bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def generate_logos(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with Image.open(ROOT / "assets" / "universal_file_utility_suite.ico") as source:
        icon = source.convert("RGBA")
    for filename, size in LOGOS.items():
        canvas = Image.new("RGBA", (size, size))
        image = icon.copy()
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
        canvas.save(destination / filename)


def find_makeappx() -> Path:
    found = shutil.which("makeappx.exe")
    if found:
        return Path(found)
    kits_root = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin"
    versions = sorted(
        (path for path in kits_root.glob("*") if re.fullmatch(r"\d+(?:\.\d+){3}", path.name)),
        key=lambda path: tuple(map(int, path.name.split("."))), reverse=True,
    )
    for version in versions:
        candidate = version / "x64" / "makeappx.exe"
        if candidate.is_file():
            return candidate
    raise RuntimeError("MakeAppx.exe is missing. Install the Windows 11 SDK: https://developer.microsoft.com/windows/downloads/windows-sdk/")


def run(command: list[str], *, log: Path | None = None) -> None:
    if log is None:
        subprocess.run(command, check=True, cwd=ROOT)
        return
    with log.open("w", encoding="utf-8") as handle:
        result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        print(log.read_text(encoding="utf-8", errors="replace")[-12000:], file=sys.stderr)
        raise RuntimeError(f"MSIX command failed ({result.returncode}); see {log}")


def probe_binary(executable: Path, work_dir: Path) -> dict[str, Any]:
    probe = subprocess.run([str(executable), "--smoke-test"], cwd=work_dir, capture_output=True, text=True, timeout=60, check=True)
    payload: dict[str, Any] = json.loads(probe.stdout)
    if payload.get("app", {}).get("version") != PACKAGE_VERSION:
        raise ValueError(f"Frozen payload version does not match {PACKAGE_VERSION}: {executable}")
    return payload


def _is_x64_executable(data: bytes) -> bool:
    if len(data) < 64 or data[:2] != b"MZ":
        return False
    offset = struct.unpack_from("<I", data, 60)[0]
    return len(data) >= offset + 6 and data[offset:offset + 4] == b"PE\0\0" and struct.unpack_from("<H", data, offset + 4)[0] == 0x8664


def validate_msix(path: Path, identity: dict[str, str], version: str, mode: str) -> dict[str, Any]:
    with zipfile.ZipFile(path) as package:
        archive_names = {unquote(name): name for name in package.namelist()}
        names = set(archive_names)
        if len(names) != len(package.infolist()):
            raise ValueError("MSIX contains duplicate archive entries.")
        required = {
            "AppxManifest.xml", "AppxBlockMap.xml", "[Content_Types].xml", "App/msix-distribution.json",
            "App/msix-build-source.json",
            "App/FormatFoundry.exe", "App/FormatFoundry_Updater.exe", "App/_internal/LICENSE",
            "App/_internal/THIRD_PARTY_NOTICES.txt", "App/_internal/assets/code_languages.json",
            *(f"Assets/{name}" for name in LOGOS),
        }
        if missing := required - names:
            raise ValueError(f"MSIX is missing required files: {sorted(missing)}")
        if "AppxSignature.p7x" in names:
            raise ValueError("This build path produces unsigned Store submissions and test candidates only.")
        manifest = ET.fromstring(package.read("AppxManifest.xml"))
        manifest_identity = manifest.find(f"{{{FOUNDATION}}}Identity")
        expected = {"Name": identity["package_name"], "Publisher": identity["publisher"], "Version": version, "ProcessorArchitecture": "x64"}
        if manifest_identity is None or manifest_identity.attrib != expected:
            raise ValueError("Manifest identity/version does not match the requested build.")
        applications = {
            app.get("Id"): app for app in manifest.findall(f"{{{FOUNDATION}}}Applications/{{{FOUNDATION}}}Application")
        }
        for app_id, executable in (("FormatFoundry", r"App\FormatFoundry.exe"), ("BackendCenter", r"App\FormatFoundry_Updater.exe")):
            app = applications.get(app_id)
            if app is None or app.get("Executable") != executable or app.get(f"{{{UAP10}}}TrustLevel") != "mediumIL":
                raise ValueError(f"MSIX is missing a desktop executable entry point: {app_id}")
        tools_visuals = applications["BackendCenter"].find(f"{{{UAP}}}VisualElements")
        if tools_visuals is None or tools_visuals.get("AppListEntry") != "none":
            raise ValueError("Optional tools must not add a second Start-menu tile.")
        metadata = json.loads(package.read("App/msix-distribution.json"))
        if metadata.get("channel") != ("microsoft-store" if mode == "store" else "development") or metadata.get("package_version") != PACKAGE_VERSION:
            raise ValueError("MSIX runtime distribution metadata is inconsistent.")
        source_evidence = json.loads(package.read("App/msix-build-source.json"))
        if not re.fullmatch(r"[0-9a-f]{64}", str(source_evidence.get("payload_source_sha256", ""))):
            raise ValueError("MSIX is missing its frozen-source fingerprint.")
        for name in ("App/FormatFoundry.exe", "App/FormatFoundry_Updater.exe"):
            if not _is_x64_executable(package.read(name)):
                raise ValueError(f"MSIX contains an invalid or non-x64 executable: {name}")
        for filename, size in LOGOS.items():
            with package.open(f"Assets/{filename}") as handle, Image.open(handle) as logo:
                if logo.size != (size, size):
                    raise ValueError(f"MSIX logo has incorrect dimensions: {filename}")
        blockmap = ET.fromstring(package.read("AppxBlockMap.xml"))
        if blockmap.get("HashMethod") != "http://www.w3.org/2001/04/xmlenc#sha256":
            raise ValueError("MSIX must use SHA-256 block hashes.")
        verified_files: set[str] = set()
        for file in blockmap.findall(f"{{{BLOCKMAP}}}File"):
            name = str(file.get("Name", "")).replace("\\", "/")
            if name not in names or name in verified_files:
                raise ValueError(f"MSIX block map has an invalid or duplicate file: {name}")
            archive_name = archive_names[name]
            if package.getinfo(archive_name).file_size != int(file.get("Size", "-1")):
                raise ValueError(f"MSIX block map size mismatch: {name}")
            with package.open(archive_name) as content:
                for block in file.findall(f"{{{BLOCKMAP}}}Block"):
                    chunk = content.read(65536)
                    if not chunk or base64.b64encode(hashlib.sha256(chunk).digest()).decode("ascii") != block.get("Hash"):
                        raise ValueError(f"MSIX block hash mismatch: {name}")
                if content.read(1):
                    raise ValueError(f"MSIX block map does not cover all content: {name}")
            verified_files.add(name)
        # The block map itself and the ZIP content type directory are not payload blocks.
        if names - {"AppxBlockMap.xml", "[Content_Types].xml"} != verified_files:
            raise ValueError("MSIX block map does not cover the entire payload.")
    with path.open("rb") as artifact:
        artifact_hash = hashlib.file_digest(artifact, "sha256").hexdigest()
    return {
        "schema": "format-foundry/msix-validation/v1", "mode": mode, "package_version": PACKAGE_VERSION,
        "display_version": DISPLAY_VERSION, "msix_version": version, "identity": identity,
        "artifact": path.name, "sha256": artifact_hash,
        "size_bytes": path.stat().st_size, "verified_blockmap_files": len(verified_files),
        "signature": "unsigned", "store_certified": False,
        "purpose": "Partner Center submission" if mode == "store" else "Local development testing only",
        "frozen_source": source_evidence,
        "validated_at_utc": datetime.now(UTC).isoformat(),
    }


def build(args: argparse.Namespace) -> Path:
    if os.name != "nt":
        raise RuntimeError("Build MSIX on x64 Windows with the Windows SDK installed.")
    identity_data = None
    if args.identity_file:
        identity_data = json.loads(Path(args.identity_file).read_text(encoding="utf-8-sig"))
    elif args.mode == "store":
        identity_data = {
            key: os.environ.get("WINDOWS_STORE_PRODUCT_ID" if key == "store_product_id" else f"WINDOWS_STORE_{key.upper()}", "")
            for key in IDENTITY_FIELDS
        }
    identity = package_identity(args.mode, identity_data)
    version = msix_version(PACKAGE_VERSION, args.store_version)
    makeappx = find_makeappx()
    payload = ROOT / "dist" / "FormatFoundry_MSIX"
    source_stamp = payload / "msix-build-source.json"
    if not args.skip_freeze:
        run([sys.executable, "-m", "tools.verify_repo_integrity", str(ROOT)])
        run([sys.executable, "tools/generate_windows_version_info.py"])
        run([sys.executable, "tools/collect_build_evidence.py", "--notices", "build/third-party-notices"])
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "FormatFoundry_MSIX.spec"])
        source_stamp.write_text(json.dumps({"payload_source_sha256": payload_source_hash()}, indent=2) + "\n", encoding="utf-8")
    if not (payload / "FormatFoundry.exe").is_file() or not (payload / "FormatFoundry_Updater.exe").is_file():
        raise RuntimeError("Frozen MSIX payload is missing. Run build_msix.ps1 without -SkipFreeze.")
    if not source_stamp.is_file() or json.loads(source_stamp.read_text(encoding="utf-8")).get("payload_source_sha256") != payload_source_hash():
        raise RuntimeError("Frozen payload does not match current source/resources. Rebuild without -SkipFreeze.")
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / f"FormatFoundry_{PACKAGE_VERSION}_x64_{'store' if args.mode == 'store' else 'development'}.msix"
    work_root = ROOT / "build" / "msix"
    work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="package-", dir=work_root) as temporary:
        work = Path(temporary)
        stage = work / "payload"
        stage.mkdir()
        shutil.copytree(payload, stage / "App")
        metadata = {
            "product_slug": PRODUCT_SLUG, "package_name": identity["package_name"],
            "channel": "microsoft-store" if args.mode == "store" else "development",
            "store_product_id": identity["store_product_id"], "package_version": PACKAGE_VERSION,
        }
        (stage / "App" / "msix-distribution.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        generate_logos(stage / "Assets")
        (stage / "AppxManifest.xml").write_bytes(manifest_bytes(identity, version))
        run([str(makeappx), "pack", "/d", str(stage), "/p", str(artifact), "/h", "SHA256", "/o"], log=work_root / f"{args.mode}-pack.log")
        report = validate_msix(artifact, identity, version, args.mode)
        extracted = work / "extracted"
        run([str(makeappx), "unpack", "/p", str(artifact), "/d", str(extracted), "/o"], log=work_root / f"{args.mode}-unpack.log")
        independent_cwd = work / "unrelated-cwd"
        independent_cwd.mkdir()
        report["frozen_smoke_tests"] = {
            name: probe_binary(extracted / "App" / name, independent_cwd)
            for name in ("FormatFoundry.exe", "FormatFoundry_Updater.exe")
        }
        report["installed_activation_tested"] = False
        report["makeappx"] = str(makeappx)
    report_path = artifact.with_suffix(".validation.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / f"SHA256SUMS-msix-{args.mode}").write_text(f"{report['sha256']}  {artifact.name}\n", encoding="ascii")
    print(f"MSIX produced: {artifact}\nValidation: {report_path}\nMSIX version: {version} ({DISPLAY_VERSION})")
    print("Store certification and installed activation are separate from this build validation.")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("candidate", "store"), default="candidate")
    parser.add_argument("--identity-file", default="")
    parser.add_argument("--store-version", default="")
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--output-dir", default=str(ROOT / "release_bins" / "msix"))
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"MSIX build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

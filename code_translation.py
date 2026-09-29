"""Bounded, compiler-backed code translation adapters for selected file pairs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from file_operation_support import commit_output, file_identity
from language_support import read_regular_file

MAX_SOURCE_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 512 * 1024
COMPILER_TIMEOUT_SECONDS = 25
PROJECT_TIMEOUT_SECONDS = 60
MAX_PROJECT_FILES = 256
MAX_PROJECT_SCAN_ENTRIES = 5000
MAX_PROJECT_FILE_BYTES = 512 * 1024
MAX_PROJECT_SOURCE_BYTES = 4 * 1024 * 1024
MAX_PROJECT_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_COMPILER_DIAGNOSTICS_BYTES = 1024 * 1024
PROJECT_INPUT_SUFFIXES = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".json"}
PROJECT_OUTPUT_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".json"}
PROJECT_IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "coverage", ".next"}
TYPESCRIPT_EXTENSIONS = {".ts": ".js", ".mts": ".mjs", ".cts": ".cjs"}
TYPESCRIPT_DOCS_URL = "https://www.typescriptlang.org/download/"


class TranslationError(RuntimeError):
    """A requested translation could not be completed safely."""


class TranslationCanceled(TranslationError):
    """The user stopped the translation before output was committed."""


@dataclass(frozen=True)
class Compiler:
    node: Path
    typescript: Path


@dataclass(frozen=True)
class TranslationResult:
    source_language: str
    target_language: str
    output_path: Path
    output_text: str
    compiler: str


@dataclass(frozen=True)
class ProjectTranslationResult:
    output_path: Path
    files: tuple[str, ...]
    input_file_count: int
    compiler: str


def supported_translation(source_id: str, target_id: str) -> bool:
    return source_id == "typescript" and target_id == "javascript"


def output_suffix(source: Path, source_id: str, target_id: str) -> str:
    if not supported_translation(source_id, target_id):
        raise TranslationError("This language pair has no verified translation adapter yet.")
    suffix = TYPESCRIPT_EXTENSIONS.get(source.suffix.casefold())
    if suffix is None:
        raise TranslationError("Choose a .ts, .mts or .cts TypeScript file. TSX needs a separate JSX build setup.")
    return suffix


def find_typescript_compiler() -> Compiler | None:
    """Find native Node and the official compiler in a project or global npm install."""
    node_raw = shutil.which("node")
    if not node_raw or (sys.platform.startswith("linux") and Path(node_raw).suffix.casefold() in {".cmd", ".bat", ".exe"}):
        return None
    node = Path(node_raw)
    candidates = [Path(__file__).resolve().parent / "node_modules" / "typescript" / "lib" / "tsc.js"]
    command = shutil.which("tsc") or shutil.which("tsc.cmd")
    if command:
        path = Path(command)
        candidates.extend((
            path.parent / "node_modules" / "typescript" / "lib" / "tsc.js",
            path.resolve().parent.parent / "lib" / "tsc.js",
            path.resolve().parent / "tsc.js",
        ))
    for script in candidates:
        if script.is_file():
            return Compiler(node=node, typescript=script.resolve())
    return None


def _run_compiler(
    command: list[str], cwd: Path, cancel_event: threading.Event | None, timeout: int,
) -> tuple[int, str]:
    with tempfile.TemporaryFile(mode="w+b") as diagnostics_file:
        try:
            process = subprocess.Popen(
                command, cwd=cwd, stdout=diagnostics_file, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
            )
        except OSError as exc:
            raise TranslationError("Could not start the TypeScript compiler. Check its Node.js installation.") from exc
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if cancel_event and cancel_event.is_set():
                    raise TranslationCanceled("Translation stopped; no output was saved.")
                if time.monotonic() >= deadline:
                    raise TranslationError("TypeScript compilation timed out; no output was saved.")
                if os.fstat(diagnostics_file.fileno()).st_size > MAX_COMPILER_DIAGNOSTICS_BYTES:
                    raise TranslationError("TypeScript produced too many diagnostics; no output was saved.")
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
        if os.fstat(diagnostics_file.fileno()).st_size > MAX_COMPILER_DIAGNOSTICS_BYTES:
            raise TranslationError("TypeScript produced too many diagnostics; no output was saved.")
        diagnostics_file.seek(0)
        return process.returncode, diagnostics_file.read().decode("utf-8", errors="replace")


def translate_file(
    source: Path,
    destination: Path,
    source_id: str,
    target_id: str,
    *,
    compiler: Compiler | None = None,
    cancel_event: threading.Event | None = None,
) -> TranslationResult:
    suffix = output_suffix(source, source_id, target_id)
    if os.path.normcase(str(source.absolute())) == os.path.normcase(str(destination.absolute())):
        raise TranslationError("The output cannot replace the source file.")
    if destination.suffix.casefold() != suffix:
        raise TranslationError(f"The output file must use {suffix} for this TypeScript source.")
    if not destination.parent.is_dir():
        raise TranslationError("Choose an existing output folder.")
    if file_identity(destination) is not None:
        raise TranslationError("Output already exists. Choose a different name to keep the original.")
    selected_compiler = compiler or find_typescript_compiler()
    if selected_compiler is None:
        raise TranslationError("TypeScript translation needs Node.js and the TypeScript compiler. Install them, then retry.")
    if not selected_compiler.node.is_file() or not selected_compiler.typescript.is_file():
        raise TranslationError("The selected TypeScript compiler is no longer available. Refresh the tool installation.")

    try:
        raw = read_regular_file(source, MAX_SOURCE_BYTES)
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TranslationError("Choose a UTF-8 TypeScript file.") from exc
    except ValueError as exc:
        raise TranslationError(str(exc)) from exc
    if any(ord(character) < 32 and character not in "\n\r\t\f" for character in text):
        raise TranslationError("Binary or control-character content is not valid TypeScript input here.")
    if cancel_event and cancel_event.is_set():
        raise TranslationCanceled("Translation stopped before compilation.")

    with tempfile.TemporaryDirectory(prefix="format-foundry-code-") as directory:
        scratch = Path(directory)
        work_input = scratch / ("input" + source.suffix.casefold())
        work_input.write_text(text, encoding="utf-8", newline="\n")
        output_dir = scratch / "out"
        output_dir.mkdir()
        command = [
            str(selected_compiler.node), str(selected_compiler.typescript), str(work_input),
            "--strict", "--isolatedModules", "--noResolve", "--noEmitOnError",
            "--target", "ES2020", "--module", "ES2020", "--lib", "ES2020,DOM",
            "--outDir", str(output_dir), "--pretty", "false", "--sourceMap", "false",
            "--declaration", "false",
        ]
        returncode, diagnostics = _run_compiler(command, scratch, cancel_event, COMPILER_TIMEOUT_SECONDS)
        if returncode != 0:
            message = (diagnostics or "TypeScript compilation failed without details.").replace(str(scratch), "<temporary>")
            raise TranslationError("TypeScript reported errors; no output was saved.\n" + message[:4000])
        produced = output_dir / ("input" + suffix)
        if not produced.is_file():
            raise TranslationError("The compiler reported success but did not create the expected JavaScript file.")
        output_bytes = read_regular_file(produced, MAX_OUTPUT_BYTES)
        try:
            output_text = output_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TranslationError("The compiler did not produce UTF-8 JavaScript output.") from exc
        if cancel_event and cancel_event.is_set():
            raise TranslationCanceled("Translation stopped; no output was saved.")

        # Stage in the destination directory so the final commit is atomic on the same filesystem.
        descriptor, staged_name = tempfile.mkstemp(prefix=".format-foundry-code-", suffix=suffix, dir=destination.parent)
        staged = Path(staged_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(output_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            if cancel_event and cancel_event.is_set():
                raise TranslationCanceled("Translation stopped; no output was saved.")
            commit_output(staged, destination, None)
        finally:
            staged.unlink(missing_ok=True)
    return TranslationResult(source_id, target_id, destination, output_text, "TypeScript compiler")


def _copy_project(project_root: Path, staged_root: Path, cancel_event: threading.Event | None) -> int:
    copied = 0
    scanned = 0
    total_bytes = 0
    resolved_root = project_root.resolve()

    def fail_walk(exc: OSError) -> None:
        raise exc

    for folder, dirs, filenames in os.walk(project_root, topdown=True, followlinks=False, onerror=fail_walk):
        relative_folder = Path(folder).relative_to(project_root)
        if len(relative_folder.parts) > 16:
            raise TranslationError("Project nesting exceeds the 16-folder limit.")
        allowed_dirs = []
        for name in sorted(dirs):
            scanned += 1
            if scanned > MAX_PROJECT_SCAN_ENTRIES:
                raise TranslationError("Project contains too many entries for a bounded compile.")
            if name.casefold() in PROJECT_IGNORED_DIRS:
                continue
            child = Path(folder) / name
            if child.is_symlink() or not child.resolve().is_relative_to(resolved_root):
                raise TranslationError("Project symlinks are not supported; use regular local files.")
            allowed_dirs.append(name)
        dirs[:] = allowed_dirs
        for name in sorted(filenames):
            scanned += 1
            if scanned > MAX_PROJECT_SCAN_ENTRIES:
                raise TranslationError("Project contains too many entries for a bounded compile.")
            if name.casefold() in {"package-lock.json", "npm-shrinkwrap.json"}:
                continue
            source = Path(folder) / name
            if source.suffix.casefold() not in PROJECT_INPUT_SUFFIXES:
                continue
            if source.is_symlink() or not source.resolve().is_relative_to(resolved_root):
                raise TranslationError("Project symlinks are not supported; use regular local files.")
            copied += 1
            if copied > MAX_PROJECT_FILES:
                raise TranslationError(f"Project exceeds the {MAX_PROJECT_FILES}-file compile limit.")
            try:
                raw = read_regular_file(source, MAX_PROJECT_FILE_BYTES)
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise TranslationError("Project files must be UTF-8 text.") from exc
            except ValueError as exc:
                raise TranslationError("Project contains a non-regular or oversized source file.") from exc
            if any(ord(character) < 32 and character not in "\n\r\t\f" for character in text):
                raise TranslationError("Project contains binary or control-character content.")
            total_bytes += len(raw)
            if total_bytes > MAX_PROJECT_SOURCE_BYTES:
                raise TranslationError("Project exceeds the 4 MiB source limit.")
            target = staged_root / relative_folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if cancel_event and cancel_event.is_set():
                raise TranslationCanceled("Translation stopped; no output was saved.")
    return copied


def _validate_project_config(config_text: str, staged_root: Path) -> None:
    try:
        config = json.loads(config_text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise TranslationError("TypeScript did not return a valid resolved project configuration.") from exc
    if not isinstance(config, dict):
        raise TranslationError("TypeScript returned an invalid project configuration.")
    if config.get("references"):
        raise TranslationError("Project references need a full build graph and are not supported in this bounded mode.")
    options = config.get("compilerOptions", {})
    if not isinstance(options, dict):
        raise TranslationError("Invalid TypeScript compiler options.")
    for name in ("out", "outFile", "declarationDir", "tsBuildInfoFile", "generateTrace", "generateCpuProfile"):
        if options.get(name):
            raise TranslationError(f"The {name} compiler option can write outside the staged output and is not supported.")
    for name in ("incremental", "composite", "emitDeclarationOnly", "noEmit", "plugins"):
        if options.get(name):
            raise TranslationError(f"The {name} compiler option is not supported in a bounded project compile.")
    project_root = staged_root.resolve()
    for name in ("outDir", "rootDir", "baseUrl"):
        value = options.get(name)
        if isinstance(value, str) and not (project_root / value).resolve().is_relative_to(project_root):
            raise TranslationError(f"The {name} compiler path must stay inside the selected project.")
    files = config.get("files")
    if not isinstance(files, list) or not files or len(files) > MAX_PROJECT_FILES:
        raise TranslationError("The resolved project must select 1 to 256 local source files.")
    for name in files:
        if not isinstance(name, str) or not (project_root / name).resolve().is_relative_to(project_root):
            raise TranslationError("The resolved project includes a file outside the selected folder.")
        if not (project_root / name).is_file():
            raise TranslationError("The resolved project includes a file unavailable in the staged copy.")


def _collect_project_output(output_root: Path) -> list[tuple[str, bytes]]:
    result: list[tuple[str, bytes]] = []
    total_bytes = 0
    scanned = 0
    for path in sorted(output_root.rglob("*")):
        scanned += 1
        if scanned > MAX_PROJECT_SCAN_ENTRIES:
            raise TranslationError("The compiler produced too many output entries.")
        if path.is_symlink():
            raise TranslationError("The compiler produced an unsupported linked output.")
        if path.is_dir():
            continue
        if not path.is_file() or path.suffix.casefold() not in PROJECT_OUTPUT_SUFFIXES:
            raise TranslationError("The compiler produced an unexpected output file.")
        try:
            raw = read_regular_file(path, MAX_PROJECT_OUTPUT_BYTES)
            raw.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise TranslationError("The compiler produced oversized or non-text output.") from exc
        total_bytes += len(raw)
        if total_bytes > MAX_PROJECT_OUTPUT_BYTES or len(result) >= MAX_PROJECT_FILES:
            raise TranslationError("Compiled project output exceeds the bounded size or file count.")
        result.append((path.relative_to(output_root).as_posix(), raw))
    if not result:
        raise TranslationError("The compiler succeeded but did not produce JavaScript output.")
    return result


def translate_project(
    project_root: Path,
    destination: Path,
    *,
    compiler: Compiler | None = None,
    cancel_event: threading.Event | None = None,
) -> ProjectTranslationResult:
    if project_root.is_symlink() or not project_root.is_dir():
        raise TranslationError("Choose a regular TypeScript project folder.")
    config_path = project_root / "tsconfig.json"
    if config_path.is_symlink() or not config_path.is_file() or not config_path.resolve().is_relative_to(project_root.resolve()):
        raise TranslationError("The project folder needs a regular tsconfig.json file.")
    if destination.suffix.casefold() != ".zip" or not destination.parent.is_dir():
        raise TranslationError("Choose a .zip filename in an existing output folder.")
    if os.path.lexists(destination):
        raise TranslationError("Output already exists. Choose another ZIP name to preserve it.")
    selected_compiler = compiler or find_typescript_compiler()
    if selected_compiler is None:
        raise TranslationError("Project translation needs Node.js and the TypeScript compiler. Install them, then retry.")
    if not selected_compiler.node.is_file() or not selected_compiler.typescript.is_file():
        raise TranslationError("The selected TypeScript compiler is no longer available.")
    if cancel_event and cancel_event.is_set():
        raise TranslationCanceled("Translation stopped; no output was saved.")

    with tempfile.TemporaryDirectory(prefix="format-foundry-project-") as directory:
        scratch = Path(directory)
        staged_root = scratch / "project"
        staged_root.mkdir()
        copied_count = _copy_project(project_root, staged_root, cancel_event)
        config = staged_root / "tsconfig.json"
        show_command = [
            str(selected_compiler.node), str(selected_compiler.typescript),
            "--project", str(config), "--showConfig", "--pretty", "false",
        ]
        returncode, diagnostics = _run_compiler(show_command, scratch, cancel_event, PROJECT_TIMEOUT_SECONDS)
        if returncode != 0:
            raise TranslationError("TypeScript could not resolve this project configuration.\n" + diagnostics.replace(str(scratch), "<temporary>")[:4000])
        _validate_project_config(diagnostics, staged_root)
        output_root = scratch / "out"
        output_root.mkdir()
        compile_command = [
            str(selected_compiler.node), str(selected_compiler.typescript), "--project", str(config),
            "--outDir", str(output_root), "--noEmitOnError", "--incremental", "false",
            "--declaration", "false", "--declarationMap", "false", "--sourceMap", "false",
            "--inlineSourceMap", "false", "--pretty", "false",
        ]
        returncode, diagnostics = _run_compiler(compile_command, scratch, cancel_event, PROJECT_TIMEOUT_SECONDS)
        if returncode != 0:
            raise TranslationError("TypeScript reported project errors; no ZIP was saved.\n" + diagnostics.replace(str(scratch), "<temporary>")[:4000])
        outputs = _collect_project_output(output_root)
        if cancel_event and cancel_event.is_set():
            raise TranslationCanceled("Translation stopped; no output was saved.")
        descriptor, staged_name = tempfile.mkstemp(prefix=".format-foundry-project-", suffix=".zip", dir=destination.parent)
        staged = Path(staged_name)
        try:
            with os.fdopen(descriptor, "w+b") as handle:
                with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                    for name, raw in outputs:
                        entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                        entry.compress_type = zipfile.ZIP_DEFLATED
                        entry.external_attr = 0o644 << 16
                        archive.writestr(entry, raw)
                        if cancel_event and cancel_event.is_set():
                            raise TranslationCanceled("Translation stopped; no output was saved.")
                handle.flush()
                os.fsync(handle.fileno())
            if staged.stat().st_size > MAX_PROJECT_OUTPUT_BYTES:
                raise TranslationError("Compiled project ZIP exceeds the 8 MiB output limit.")
            if cancel_event and cancel_event.is_set():
                raise TranslationCanceled("Translation stopped; no output was saved.")
            try:
                commit_output(staged, destination, None)
            except FileExistsError as exc:
                raise TranslationError("Output appeared while compiling; no file was replaced.") from exc
        finally:
            staged.unlink(missing_ok=True)
    return ProjectTranslationResult(destination, tuple(name for name, _ in outputs), copied_count, "TypeScript compiler")

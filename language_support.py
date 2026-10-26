"""Offline reference data and read-only source inspection, never code execution."""

import ast
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

LIBRARY_PATH = Path(__file__).resolve().parent / "assets" / "code_languages.json"
MAX_LIBRARY_BYTES = 512 * 1024
MAX_SOURCE_BYTES = 64 * 1024
RULE_TOPICS = (
    "types", "blocks", "comments", "variables", "functions", "control_flow",
    "collections", "errors", "modules", "runtime",
)
CATEGORIES = {"Programming", "Shell", "Query", "Markup", "Stylesheet"}
REFERENCE_NOTICE = (
    "Offline core reference, not a complete grammar, compiler or automatic translator. "
    "Rules describe the stated baseline; libraries, dialects and newer features may differ."
)
TRANSLATION_NOTICE = (
    "This comparison does not generate code. Similar syntax does not guarantee equivalent behavior. "
    "A port needs dependency/API mapping, target-specific design and tests for inputs, outputs and side effects."
)


class LanguageLibraryError(ValueError):
    """Invalid or unavailable bundled reference data."""


@dataclass(frozen=True)
class LanguageProfile:
    id: str
    name: str
    category: str
    baseline: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...]
    rules: tuple[tuple[str, str], ...]
    example: str
    pitfalls: tuple[str, ...]
    reference_url: str

    def rule(self, topic: str) -> str:
        return dict(self.rules)[topic]


@dataclass(frozen=True)
class LanguageLibrary:
    revision: str
    profiles: tuple[LanguageProfile, ...]

    def search(self, query: str = "") -> tuple[LanguageProfile, ...]:
        terms = query.casefold().split()
        return tuple(profile for profile in self.profiles if all(
            term in " ".join((
                profile.name, profile.id, profile.category, profile.baseline,
                *profile.aliases, *profile.extensions, *(text for _, text in profile.rules), *profile.pitfalls,
                *RULE_TOPICS,
            )).casefold() for term in terms
        ))

    def candidates(self, filename: str) -> tuple[LanguageProfile, ...]:
        suffix = Path(filename).suffix.casefold()
        return tuple(profile for profile in self.profiles if suffix in profile.extensions)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 12000 or "\x00" in value:
        raise LanguageLibraryError(f"Invalid language library field: {field}.")
    return value


def _strings(value: object, field: str, *, empty_ok: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not empty_ok) or len(value) > 50:
        raise LanguageLibraryError(f"Invalid language library list: {field}.")
    result = tuple(_text(item, field) for item in value)
    if len(set(result)) != len(result):
        raise LanguageLibraryError(f"Duplicate language library values: {field}.")
    return result


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LanguageLibraryError("Duplicate JSON field in language library.")
        result[key] = value
    return result


def read_regular_file(path: Path, limit: int) -> bytes:
    # Nonblocking on POSIX prevents a swapped FIFO from hanging a worker on open.
    if not path.is_file():
        raise ValueError("Choose a regular file, not a folder or device.")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Choose a regular file, not a folder or device.")
        if info.st_size > limit:
            raise ValueError(f"File exceeds the {limit // 1024} KiB inspection limit.")
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"File exceeds the {limit // 1024} KiB inspection limit.")
    return raw


def load_language_library(path: Path = LIBRARY_PATH) -> LanguageLibrary:
    try:
        data = json.loads(read_regular_file(path, MAX_LIBRARY_BYTES), object_pairs_hook=_unique_object)
    except (OSError, ValueError, RecursionError) as exc:
        raise LanguageLibraryError("Cannot read the bundled language library. Repair or reinstall this build.") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "revision", "languages"}:
        raise LanguageLibraryError("Invalid language library document.")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise LanguageLibraryError("Unsupported language library schema.")
    revision = _text(data["revision"], "revision")
    entries = data["languages"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise LanguageLibraryError("Invalid language profile collection.")
    profiles = []
    ids: set[str] = set()
    names: set[str] = set()
    fields = {"id", "name", "category", "baseline", "extensions", "aliases", "rules", "example", "pitfalls", "reference_url"}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise LanguageLibraryError("Invalid language profile fields.")
        identifier = _text(entry["id"], "id")
        name = _text(entry["name"], "name")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", identifier) or identifier in ids or name.casefold() in names:
            raise LanguageLibraryError("Invalid or duplicate language identity.")
        ids.add(identifier)
        names.add(name.casefold())
        category = _text(entry["category"], "category")
        if category not in CATEGORIES:
            raise LanguageLibraryError("Invalid language category.")
        extensions = _strings(entry["extensions"], "extensions")
        if any(not re.fullmatch(r"\.[a-z0-9]+", ext) for ext in extensions):
            raise LanguageLibraryError("Invalid language extension.")
        rules = entry["rules"]
        if not isinstance(rules, dict) or set(rules) != set(RULE_TOPICS):
            raise LanguageLibraryError("Language rules must cover every core topic.")
        reference = _text(entry["reference_url"], "reference_url")
        try:
            parsed = urlsplit(reference)
            valid_url = parsed.scheme == "https" and bool(parsed.hostname) and not (parsed.username or parsed.password or parsed.port)
        except ValueError:
            valid_url = False
        if not valid_url:
            raise LanguageLibraryError("Language references must be HTTPS documentation links.")
        profiles.append(LanguageProfile(
            id=identifier, name=name, category=category, baseline=_text(entry["baseline"], "baseline"),
            extensions=extensions, aliases=_strings(entry["aliases"], "aliases", empty_ok=True),
            rules=tuple((topic, _text(rules[topic], topic)) for topic in RULE_TOPICS),
            example=_text(entry["example"], "example"), pitfalls=_strings(entry["pitfalls"], "pitfalls"),
            reference_url=reference,
        ))
    return LanguageLibrary(revision=revision, profiles=tuple(profiles))


@lru_cache(maxsize=1)
def bundled_language_library() -> LanguageLibrary:
    return load_language_library()


def format_profile(profile: LanguageProfile, revision: str) -> str:
    sections = [
        f"{profile.name} | {profile.category}", f"Baseline: {profile.baseline}",
        f"File hints: {', '.join(profile.extensions)} (extensions are not proof of language)",
        f"Library revision: {revision}", REFERENCE_NOTICE,
    ]
    sections.extend(f"{topic.replace('_', ' ').title()}\n{text}" for topic, text in profile.rules)
    sections.extend((
        "Original example (display only; never executed here)\n" + profile.example,
        "Porting pitfalls\n" + "\n".join(f"- {item}" for item in profile.pitfalls),
        f"Official documentation (opens your browser only on request):\n{profile.reference_url}",
    ))
    return "\n\n".join(sections)


def compare_languages(source: LanguageProfile, target: LanguageProfile) -> str:
    sections = [f"{source.name} -> {target.name}: reference comparison", TRANSLATION_NOTICE]
    if source.id == target.id:
        sections.append("Same language selected. Compare a different language to review porting differences.")
    if source.category != target.category:
        sections.append("Different language categories: these may describe different parts of a system, not interchangeable programs.")
    sections.extend(
        f"{topic.replace('_', ' ').title()}\n{source.name}: {source.rule(topic)}\n{target.name}: {target.rule(topic)}"
        for topic in RULE_TOPICS
    )
    for profile in (source, target):
        sections.append(f"{profile.name} pitfalls\n" + "\n".join(f"- {item}" for item in profile.pitfalls))
    sections.append("Verification checklist\n- Map libraries and external APIs.\n- Check number, string and null semantics.\n"
                    "- Check mutation, ownership, concurrency and error handling.\n- Test both implementations in an appropriate "
                    "isolated environment; Format Foundry does not execute them.")
    return "\n\n".join(sections)


def inspect_source(path: Path, library: LanguageLibrary) -> str:
    """Read one bounded UTF-8 file; do not execute, import, persist or upload its contents."""
    raw = read_regular_file(path, MAX_SOURCE_BYTES)
    try:
        source = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Use a UTF-8 source file; other encodings are not decoded automatically.") from exc
    if any(ord(char) < 32 and char not in "\n\r\t\f" for char in source):
        raise ValueError("Binary or control-character content is not a supported source file.")
    candidates = library.candidates(path.name)
    sections = [
        "Read-only source inspection", f"Size: {len(raw)} bytes | Lines: {len(source.splitlines())}",
        "Extension hints: " + (", ".join(profile.name for profile in candidates) or "Unknown"),
        "File contents are not executed, uploaded, saved or included in this report. No dependencies are imported.",
    ]
    if len(candidates) > 1:
        sections.append("Ambiguous extension. Choose a reference profile yourself; no language was assumed.")
    if len(candidates) == 1 and candidates[0].id == "python":
        sections.append(f"Python AST parsing only, using this build's Python {sys.version_info.major}.{sys.version_info.minor}.")
        try:
            ast.parse(source, filename="<selected source>")
        except SyntaxError as exc:
            sections.append(f"AST parse failed at line {exc.lineno or '?'}, column {exc.offset or '?'}. "
                            "Source text and diagnostics that may contain source are omitted for privacy.")
        except (ValueError, RecursionError, MemoryError):
            sections.append("AST parse could not complete within parser limits. Simplify or split the file.")
        else:
            sections.append("AST parsing succeeded. This does not check scope, types, dependencies, runtime behavior or safety.")
    else:
        sections.append("Reference-only inspection: no syntax parser or compiler is provided for this language.")
    sections.append(TRANSLATION_NOTICE)
    return "\n\n".join(sections)

from __future__ import annotations

import glob
import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BackendDefinition:
    name: str
    key: str
    description: str
    enables: str
    homepage: str
    docs: str
    download: str
    executables: tuple[str, ...]
    winget_id: str
    linux_packages: dict[str, tuple[str, ...]]
    install_group: str


BACKEND_DEFINITIONS: tuple[BackendDefinition, ...] = (
    BackendDefinition(
        name="FFmpeg",
        key="ffmpeg",
        description="Media engine for converting, compressing, extracting, and preparing audio and video.",
        enables="Audio and video conversion, extraction, compression, and media prep",
        homepage="https://ffmpeg.org/",
        docs="https://ffmpeg.org/documentation.html",
        download="https://ffmpeg.org/download.html",
        executables=("ffmpeg", "ffmpeg.exe"),
        winget_id="Gyan.FFmpeg",
        linux_packages={"apt": ("ffmpeg",), "dnf": ("ffmpeg",), "pacman": ("ffmpeg",), "zypper": ("ffmpeg",)},
        install_group="ffmpeg",
    ),
    BackendDefinition(
        name="FFprobe",
        key="ffprobe",
        description="Media inspection companion installed with FFmpeg.",
        enables="Stream details, duration checks, and media metadata inspection",
        homepage="https://ffmpeg.org/ffprobe.html",
        docs="https://ffmpeg.org/ffprobe.html",
        download="https://ffmpeg.org/download.html",
        executables=("ffprobe", "ffprobe.exe"),
        winget_id="Gyan.FFmpeg",
        linux_packages={"apt": ("ffmpeg",), "dnf": ("ffmpeg",), "pacman": ("ffmpeg",), "zypper": ("ffmpeg",)},
        install_group="ffmpeg",
    ),
    BackendDefinition(
        name="Pandoc",
        key="pandoc",
        description="Document converter for markup and publishing-oriented formats.",
        enables="Markdown, HTML, DOCX, EPUB, and related document conversions",
        homepage="https://pandoc.org/",
        docs="https://pandoc.org/MANUAL.html",
        download="https://pandoc.org/installing.html",
        executables=("pandoc", "pandoc.exe"),
        winget_id="JohnMacFarlane.Pandoc",
        linux_packages={"apt": ("pandoc",), "dnf": ("pandoc",), "pacman": ("pandoc",), "zypper": ("pandoc",)},
        install_group="pandoc",
    ),
    BackendDefinition(
        name="LibreOffice",
        key="libreoffice",
        description="Office document engine used for compatible headless conversions.",
        enables="Office document conversion and broader PDF/document compatibility",
        homepage="https://www.libreoffice.org/",
        docs="https://help.libreoffice.org/latest/en-US/text/shared/guide/start_center.html",
        download="https://www.libreoffice.org/download/download-libreoffice/",
        executables=("soffice", "soffice.exe"),
        winget_id="TheDocumentFoundation.LibreOffice",
        linux_packages={
            "apt": ("libreoffice",),
            "dnf": ("libreoffice",),
            "pacman": ("libreoffice-fresh",),
            "zypper": ("libreoffice",),
        },
        install_group="libreoffice",
    ),
    BackendDefinition(
        name="7-Zip",
        key="sevenzip",
        description="Archive utility for formats beyond the built-in ZIP and TAR support.",
        enables="7z and additional archive extraction and packaging workflows",
        homepage="https://www.7-zip.org/",
        docs="https://7-zip.org/7z.html",
        download="https://www.7-zip.org/download.html",
        executables=("7z", "7zz", "7z.exe"),
        winget_id="7zip.7zip",
        linux_packages={
            "apt": ("p7zip-full",),
            "dnf": ("p7zip", "p7zip-plugins"),
            "pacman": ("p7zip",),
            "zypper": ("7zip",),
        },
        install_group="sevenzip",
    ),
    BackendDefinition(
        name="ImageMagick",
        key="imagemagick",
        description="Advanced image engine for camera-raw and specialist formats.",
        enables="Camera-raw input, JPEG XL, and advanced image format fallbacks",
        homepage="https://imagemagick.org/",
        docs="https://imagemagick.org/script/command-line-tools.php",
        download="https://imagemagick.org/script/download.php",
        executables=("magick", "magick.exe", "convert"),
        winget_id="ImageMagick.ImageMagick",
        linux_packages={
            "apt": ("imagemagick",),
            "dnf": ("ImageMagick",),
            "pacman": ("imagemagick",),
            "zypper": ("ImageMagick",),
        },
        install_group="imagemagick",
    ),
    BackendDefinition(
        name="Aria2",
        key="aria2",
        description="Download engine for HTTP(S), FTP, SFTP, Metalink, and BitTorrent transfers.",
        enables="Aria2 downloads, torrent selection, and torrent download workflows",
        homepage="https://aria2.github.io/",
        docs="https://aria2.github.io/manual/en/html/aria2c.html",
        download="https://github.com/aria2/aria2/releases",
        executables=("aria2c", "aria2c.exe"),
        winget_id="aria2.aria2",
        linux_packages={"apt": ("aria2",), "dnf": ("aria2",), "pacman": ("aria2",), "zypper": ("aria2",)},
        install_group="aria2",
    ),
)

BACKENDS_BY_NAME = {definition.name: definition for definition in BACKEND_DEFINITIONS}
BACKENDS_BY_KEY = {definition.key: definition for definition in BACKEND_DEFINITIONS}
BACKEND_DESCRIPTIONS = {definition.name: definition.description for definition in BACKEND_DEFINITIONS}
BACKEND_LINKS = {
    definition.name: {
        "homepage": definition.homepage,
        "docs": definition.docs,
        "download": definition.download,
        "install_cmd_windows": (
            f"winget install --id {definition.winget_id} --exact --source winget "
            "--accept-package-agreements --accept-source-agreements"
        ),
    }
    for definition in BACKEND_DEFINITIONS
}


def current_platform_key() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    return "other"


def detect_linux_package_manager() -> str:
    for manager in ("apt-get", "apt", "dnf", "pacman", "zypper"):
        if shutil.which(manager):
            return "apt" if manager in {"apt", "apt-get"} else manager
    return ""


def _existing(value: str | os.PathLike[str] | None) -> str | None:
    if not value:
        return None
    try:
        candidate = Path(value)
        return str(candidate) if candidate.exists() else None
    except OSError:
        return None


def _first_existing(candidates: Iterable[str | os.PathLike[str] | None]) -> str | None:
    for candidate in candidates:
        found = _existing(candidate)
        if found:
            return found
    return None


def _first_glob(patterns: Iterable[str]) -> str | None:
    for pattern in patterns:
        if not pattern:
            continue
        try:
            for candidate in sorted(glob.glob(pattern, recursive=True)):
                found = _existing(candidate)
                if found:
                    return found
        except (OSError, ValueError):
            continue
    return None


def _env_path(name: str, *parts: str) -> Path | None:
    root = os.environ.get(name, "").strip()
    return Path(root).joinpath(*parts) if root else None


def detect_backend_paths(ffmpeg_fallback: str | None = None) -> dict[str, str | None]:
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    winget_packages = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages" if local_appdata else None

    ffmpeg = _first_existing(
        [
            shutil.which("ffmpeg") or shutil.which("ffmpeg.exe"),
            _env_path("ProgramFiles", "ffmpeg", "bin", "ffmpeg.exe"),
            _env_path("ProgramFiles(x86)", "ffmpeg", "bin", "ffmpeg.exe"),
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
        ]
    )
    if not ffmpeg and winget_packages:
        ffmpeg = _first_glob(
            [
                str(winget_packages / "Gyan.FFmpeg_Microsoft.Winget.Source_*" / "**" / "ffmpeg.exe"),
                str(winget_packages / "FFmpeg.*_Microsoft.Winget.Source_*" / "**" / "ffmpeg.exe"),
            ]
        )
    ffmpeg = ffmpeg or _existing(ffmpeg_fallback)

    ffprobe_candidates: list[str | os.PathLike[str] | None] = [
        shutil.which("ffprobe") or shutil.which("ffprobe.exe"),
        Path(ffmpeg).with_name("ffprobe.exe") if ffmpeg else None,
        Path(ffmpeg).with_name("ffprobe") if ffmpeg else None,
        "/usr/bin/ffprobe",
        "/usr/local/bin/ffprobe",
    ]
    ffprobe = _first_existing(ffprobe_candidates)
    if not ffprobe and winget_packages:
        ffprobe = _first_glob(
            [
                str(winget_packages / "Gyan.FFmpeg_Microsoft.Winget.Source_*" / "**" / "ffprobe.exe"),
                str(winget_packages / "FFmpeg.*_Microsoft.Winget.Source_*" / "**" / "ffprobe.exe"),
            ]
        )

    pandoc = _first_existing(
        [
            shutil.which("pandoc") or shutil.which("pandoc.exe"),
            _env_path("ProgramFiles", "Pandoc", "pandoc.exe"),
            _env_path("ProgramFiles(x86)", "Pandoc", "pandoc.exe"),
            _env_path("LOCALAPPDATA", "Pandoc", "pandoc.exe"),
            _env_path("LOCALAPPDATA", "Programs", "Pandoc", "pandoc.exe"),
            "/usr/bin/pandoc",
            "/usr/local/bin/pandoc",
        ]
    )
    if not pandoc and winget_packages:
        pandoc = _first_glob([str(winget_packages / "JohnMacFarlane.Pandoc_Microsoft.Winget.Source_*" / "**" / "pandoc.exe")])

    libreoffice = _first_existing(
        [
            shutil.which("soffice") or shutil.which("soffice.exe"),
            _env_path("ProgramFiles", "LibreOffice", "program", "soffice.exe"),
            _env_path("ProgramFiles(x86)", "LibreOffice", "program", "soffice.exe"),
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/usr/lib/libreoffice/program/soffice",
        ]
    )

    sevenzip = _first_existing(
        [
            shutil.which("7z") or shutil.which("7zz") or shutil.which("7z.exe"),
            _env_path("ProgramFiles", "7-Zip", "7z.exe"),
            _env_path("ProgramFiles(x86)", "7-Zip", "7z.exe"),
            _env_path("LOCALAPPDATA", "Programs", "7-Zip", "7z.exe"),
            "/usr/bin/7z",
            "/usr/bin/7zz",
            "/usr/local/bin/7z",
        ]
    )

    imagemagick = _first_existing(
        [
            shutil.which("magick") or shutil.which("magick.exe"),
            shutil.which("convert") if current_platform_key() == "linux" else None,
            "/usr/bin/magick",
            "/usr/local/bin/magick",
            "/usr/bin/convert",
        ]
    )
    if not imagemagick:
        imagemagick = _first_glob(
            [
                str(_env_path("ProgramFiles", "ImageMagick*", "magick.exe") or ""),
                str(_env_path("ProgramFiles(x86)", "ImageMagick*", "magick.exe") or ""),
                str(_env_path("LOCALAPPDATA", "Programs", "ImageMagick*", "magick.exe") or ""),
                str(winget_packages / "ImageMagick.ImageMagick_Microsoft.Winget.Source_*" / "**" / "magick.exe") if winget_packages else "",
            ]
        )

    aria2 = _first_existing(
        [
            shutil.which("aria2c") or shutil.which("aria2c.exe"),
            _env_path("ProgramFiles", "aria2", "aria2c.exe"),
            _env_path("ProgramFiles(x86)", "aria2", "aria2c.exe"),
            _env_path("LOCALAPPDATA", "Programs", "aria2", "aria2c.exe"),
            _env_path("LOCALAPPDATA", "Microsoft", "WinGet", "Links", "aria2c.exe"),
            "/usr/bin/aria2c",
            "/usr/local/bin/aria2c",
            "/snap/bin/aria2c",
        ]
    )
    if not aria2 and winget_packages:
        aria2 = _first_glob([str(winget_packages / "aria2.aria2_Microsoft.Winget.Source_*" / "**" / "aria2c.exe")])

    return {
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "pandoc": pandoc,
        "libreoffice": libreoffice,
        "sevenzip": sevenzip,
        "imagemagick": imagemagick,
        "aria2": aria2,
    }


def backend_install_command(
    backend_name: str,
    *,
    platform_key: str | None = None,
    package_manager: str | None = None,
) -> str:
    definition = BACKENDS_BY_NAME.get(backend_name)
    if definition is None:
        return ""
    platform_value = platform_key or current_platform_key()
    if platform_value == "windows":
        return BACKEND_LINKS[backend_name]["install_cmd_windows"]
    if platform_value != "linux":
        return ""
    manager = package_manager or detect_linux_package_manager()
    packages = definition.linux_packages.get(manager, ())
    if not manager or not packages:
        return ""
    quoted_packages = " ".join(shlex.quote(package) for package in packages)
    if manager == "apt":
        return f"sudo apt install -y {quoted_packages}"
    if manager == "dnf":
        return f"sudo dnf install -y {quoted_packages}"
    if manager == "pacman":
        return f"sudo pacman -S --noconfirm {quoted_packages}"
    if manager == "zypper":
        return f"sudo zypper --non-interactive install {quoted_packages}"
    return ""


def backend_install_process_args(
    backend_name: str,
    *,
    platform_key: str | None = None,
    package_manager: str | None = None,
    executable_override: str | None = None,
    privilege_helper_override: str | None = None,
) -> tuple[list[str], str]:
    definition = BACKENDS_BY_NAME.get(backend_name)
    if definition is None:
        return [], "Unknown backend."
    platform_value = platform_key or current_platform_key()
    if platform_value == "windows":
        winget = executable_override or shutil.which("winget") or shutil.which("winget.exe")
        if not winget:
            return [], "Windows Package Manager (winget) is not available. Use the official download link instead."
        return [
            winget,
            "install",
            "--id",
            definition.winget_id,
            "--exact",
            "--source",
            "winget",
            "--accept-package-agreements",
            "--accept-source-agreements",
            "--disable-interactivity",
        ], ""
    if platform_value != "linux":
        return [], "Direct backend installation is currently supported on Windows and Linux."

    manager = package_manager or detect_linux_package_manager()
    packages = definition.linux_packages.get(manager, ())
    if not manager or not packages:
        return [], "No supported Linux package manager was detected. Use the official download link instead."
    pkexec = privilege_helper_override or shutil.which("pkexec")
    if not pkexec:
        return [], "Graphical administrator approval (pkexec) is unavailable. Copy the install command and run it in a terminal."
    manager_binary_name = "apt-get" if manager == "apt" else manager
    manager_path = executable_override or shutil.which(manager_binary_name) or shutil.which(manager)
    if not manager_path:
        return [], f"The {manager} package manager executable was not found."
    if manager == "apt":
        args = [pkexec, manager_path, "install", "-y", *packages]
    elif manager == "dnf":
        args = [pkexec, manager_path, "install", "-y", *packages]
    elif manager == "pacman":
        args = [pkexec, manager_path, "-S", "--noconfirm", *packages]
    else:
        args = [pkexec, manager_path, "--non-interactive", "install", *packages]
    return args, ""


def unique_install_targets(backend_names: Iterable[str]) -> list[str]:
    selected: list[str] = []
    seen_groups: set[str] = set()
    for backend_name in backend_names:
        definition = BACKENDS_BY_NAME.get(backend_name)
        if definition is None or definition.install_group in seen_groups:
            continue
        seen_groups.add(definition.install_group)
        selected.append(backend_name)
    return selected

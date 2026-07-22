#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
SELF_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
BOOTSTRAP_VENV_DIR="${ROOT}/.venv"
UBUNTU_PREREQ_CMD="sudo apt update && sudo apt install -y python3 python3-venv python3-tk tk-dev dpkg-dev curl appstream"

print_linux_prereq_help() {
  cat >&2 <<EOF
Missing Linux build prerequisites.

Ubuntu / Debian install command:
  ${UBUNTU_PREREQ_CMD}

Notes:
  - Fix unrelated broken third-party apt repositories first if 'apt update' fails.
  - Do not run system-wide 'pip install' for this project on Ubuntu 24.04.
  - This build script creates and uses a repo-local virtual environment automatically.
EOF
}

require_command_or_exit() {
  local command_name="$1"
  local package_hint="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    return 0
  fi
  echo "Missing required command: ${command_name} (${package_hint})" >&2
  print_linux_prereq_help
  exit 1
}

require_python_module_or_exit() {
  local python_bin="$1"
  local module_name="$2"
  local package_hint="$3"
  if "$python_bin" - "$module_name" >/dev/null 2>&1 <<'PY'
import importlib.util
import sys

module_name = sys.argv[1]
sys.exit(0 if importlib.util.find_spec(module_name) else 1)
PY
  then
    return 0
  fi
  echo "Missing required Python module '${module_name}' (${package_hint})" >&2
  print_linux_prereq_help
  exit 1
}

bootstrap_local_virtualenv() {
  require_command_or_exit python3 "python3"
  require_command_or_exit curl "curl"
  require_command_or_exit sha256sum "coreutils"
  require_command_or_exit dpkg-deb "dpkg-dev"
  require_command_or_exit appstreamcli "appstream"
  require_python_module_or_exit python3 venv "python3-venv"
  require_python_module_or_exit python3 tkinter "python3-tk"

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    return 0
  fi

  if [[ ! -x "${BOOTSTRAP_VENV_DIR}/bin/python" ]]; then
    echo "Creating local build virtual environment in ${BOOTSTRAP_VENV_DIR}..."
    python3 -m venv "${BOOTSTRAP_VENV_DIR}"
  fi

  export VIRTUAL_ENV="${BOOTSTRAP_VENV_DIR}"
  export PATH="${BOOTSTRAP_VENV_DIR}/bin:${PATH}"
  hash -r
  exec /usr/bin/env bash "$SELF_PATH" "$@"
}

bootstrap_local_virtualenv "$@"

PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Active virtual environment is missing python: ${PYTHON_BIN}" >&2
  print_linux_prereq_help
  exit 1
fi

require_command_or_exit curl "curl"
require_command_or_exit sha256sum "coreutils"
require_command_or_exit dpkg-deb "dpkg-dev"
require_command_or_exit appstreamcli "appstream"
require_python_module_or_exit "${PYTHON_BIN}" tkinter "python3-tk"

echo "[preflight] Verifying repo integrity..."
"${PYTHON_BIN}" -m tools.verify_repo_integrity "${ROOT}"

APP_NAME="Format Foundry"
APP_BINARY_NAME="FormatFoundry"
UPDATER_BINARY_NAME="FormatFoundry_Updater"
PACKAGE_NAME="format-foundry"
DESKTOP_ID="io.github.pugmaster04.formatfoundry.desktop"
APPDATA_OUTPUT_NAME="${DESKTOP_ID%.desktop}.appdata.xml"
PACKAGING_ROOT="packaging/linux"
BUILD_ROOT="build/linux-packaging"
PACKAGING_WORK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/format-foundry-packaging.XXXXXX")"
APPDIR_ROOT="${PACKAGING_WORK_ROOT}/AppDir"
DEB_ROOT="${PACKAGING_WORK_ROOT}/deb-root"
ICON_OUTPUT="${BUILD_ROOT}/${PACKAGE_NAME}.png"
DESKTOP_TEMPLATE="${PACKAGING_ROOT}/${PACKAGE_NAME}.desktop.in"
APPDATA_TEMPLATE="${PACKAGING_ROOT}/${PACKAGE_NAME}.appdata.xml"
APP_RUN_TEMPLATE="${PACKAGING_ROOT}/AppRun"
APPIMAGE_TOOL_DIR="${BUILD_ROOT}/tools"

cleanup_packaging_workspace() {
  if [[ -n "${PACKAGING_WORK_ROOT:-}" && -d "${PACKAGING_WORK_ROOT}" ]]; then
    rm -rf -- "${PACKAGING_WORK_ROOT}"
  fi
}
trap cleanup_packaging_workspace EXIT

ARCH="$(uname -m)"
case "$ARCH" in
  amd64|x86_64)
    ARCH="x86_64"
    DEB_ARCH="amd64"
    APPIMAGE_ARCH="x86_64"
    ;;
  aarch64|arm64)
    ARCH="arm64"
    DEB_ARCH="arm64"
    APPIMAGE_ARCH="aarch64"
    ;;
  *)
    echo "Unsupported Linux architecture for packaging: ${ARCH}" >&2
    exit 1
    ;;
esac

PACKAGE_VERSION="$("${PYTHON_BIN}" tools/extract_app_version.py)"
DEBIAN_VERSION="${PACKAGE_VERSION/-beta/~beta}"

TAR_BASENAME="${APP_BINARY_NAME}_linux_${PACKAGE_VERSION}_${ARCH}"
TAR_DIR="release_bins/${TAR_BASENAME}"
TAR_PACKAGE="release_bins/${TAR_BASENAME}.tar.gz"
DEB_PACKAGE="release_bins/${PACKAGE_NAME}_${PACKAGE_VERSION}_${DEB_ARCH}.deb"
APPIMAGE_PACKAGE="release_bins/${APP_BINARY_NAME}_linux_${PACKAGE_VERSION}_${ARCH}.AppImage"
APPIMAGE_TOOL="${APPIMAGE_TOOL_DIR}/appimagetool-${APPIMAGE_ARCH}.AppImage"
APPIMAGE_TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${APPIMAGE_ARCH}.AppImage"
case "$APPIMAGE_ARCH" in
  x86_64)
    APPIMAGE_TOOL_SHA256="${APPIMAGE_TOOL_SHA256:-a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0}"
    ;;
  aarch64)
    APPIMAGE_TOOL_SHA256="${APPIMAGE_TOOL_SHA256:-1b00524ba8c6b678dc15ef88a5c25ec24def36cdfc7e3abb32ddcd068e8007fe}"
    ;;
esac

render_desktop_file() {
  local exec_target="$1"
  local output_path="$2"
  sed "s|__EXEC__|${exec_target}|g; s/\r$//" "$DESKTOP_TEMPLATE" > "$output_path"
}

build_linux_icon() {
  "${PYTHON_BIN}" - <<'PY'
from pathlib import Path
import shutil

dst = Path("build/linux-packaging/format-foundry.png")
dst.parent.mkdir(parents=True, exist_ok=True)
src_ico = Path("assets/universal_file_utility_suite.ico")
src_png = Path("assets/universal_file_utility_suite_preview.png")

try:
    from PIL import Image
    with Image.open(src_ico) as image:
        image = image.convert("RGBA")
        image.save(dst, format="PNG")
except Exception:
    shutil.copyfile(src_png, dst)
PY
}

download_appimagetool() {
  mkdir -p "$APPIMAGE_TOOL_DIR"
  if [[ -f "$APPIMAGE_TOOL" ]] && ! echo "${APPIMAGE_TOOL_SHA256}  ${APPIMAGE_TOOL}" | sha256sum --check --status; then
    echo "Discarding cached appimagetool because its SHA256 does not match."
    rm -f "$APPIMAGE_TOOL"
  fi
  if [[ ! -f "$APPIMAGE_TOOL" ]]; then
    echo "Downloading appimagetool for ${APPIMAGE_ARCH}..."
    curl --fail --location --proto '=https' --tlsv1.2 "$APPIMAGE_TOOL_URL" -o "$APPIMAGE_TOOL"
  fi
  echo "${APPIMAGE_TOOL_SHA256}  ${APPIMAGE_TOOL}" | sha256sum --check --status || {
    echo "appimagetool SHA256 verification failed. Refusing to execute ${APPIMAGE_TOOL}." >&2
    rm -f "$APPIMAGE_TOOL"
    exit 1
  }
  chmod +x "$APPIMAGE_TOOL"
}

echo "[1/8] Installing Python dependencies..."
"${PYTHON_BIN}" -m pip install -r requirements.txt

echo "[2/8] Building app binary..."
"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean FormatFoundry.spec

echo "[3/8] Building updater binary..."
"${PYTHON_BIN}" -m PyInstaller --noconfirm --clean FormatFoundry_Updater.spec

echo "[4/8] Staging binaries..."
mkdir -p release_bins
rm -f \
  "release_bins/${APP_BINARY_NAME}" \
  "release_bins/${UPDATER_BINARY_NAME}" \
  "release_bins/UniversalConversionHub_UCH" \
  "release_bins/UniversalConversionHub_UCH_Updater" \
  "release_bins/UniversalConversionHub_HCB" \
  "release_bins/UniversalConversionHub_HCB_Updater" \
  "release_bins/UniversalFileUtilitySuite" \
  "release_bins/UniversalFileUtilitySuite_Updater" \
  "$TAR_PACKAGE" \
  "$DEB_PACKAGE" \
  "$APPIMAGE_PACKAGE" \
  release_bins/UniversalConversionHub_UCH_linux_*.tar.gz \
  release_bins/FormatFoundry_linux_*.tar.gz \
  release_bins/*.deb \
  release_bins/*.AppImage
rm -rf "$TAR_DIR" "$APPDIR_ROOT" "$DEB_ROOT" "$BUILD_ROOT/deb-smoke"

cp -f "dist/${APP_BINARY_NAME}" "release_bins/${APP_BINARY_NAME}"
cp -f "dist/${UPDATER_BINARY_NAME}" "release_bins/${UPDATER_BINARY_NAME}"
chmod +x "release_bins/${APP_BINARY_NAME}" "release_bins/${UPDATER_BINARY_NAME}"

echo "[5/8] Creating Linux tar.gz package..."
mkdir -p "$TAR_DIR"
cp -f "dist/${APP_BINARY_NAME}" "$TAR_DIR/${APP_BINARY_NAME}"
cp -f "dist/${UPDATER_BINARY_NAME}" "$TAR_DIR/${UPDATER_BINARY_NAME}"
cp -f "README.md" "$TAR_DIR/README.md"
cp -f "PROJECT_PLAN.md" "$TAR_DIR/PROJECT_PLAN.md"
cp -f "update_manifest.example.json" "$TAR_DIR/update_manifest.example.json"
cp -f "LICENSE" "$TAR_DIR/LICENSE"
chmod +x "$TAR_DIR/${APP_BINARY_NAME}" "$TAR_DIR/${UPDATER_BINARY_NAME}"
tar -czf "$TAR_PACKAGE" -C release_bins "$TAR_BASENAME"

echo "[6/8] Creating Debian package..."
build_linux_icon
mkdir -p \
  "${DEB_ROOT}/DEBIAN" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}" \
  "${DEB_ROOT}/usr/bin" \
  "${DEB_ROOT}/usr/share/applications" \
  "${DEB_ROOT}/usr/share/doc/${PACKAGE_NAME}" \
  "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps" \
  "${DEB_ROOT}/usr/share/pixmaps" \
  "${DEB_ROOT}/usr/share/metainfo"
cp -f "dist/${APP_BINARY_NAME}" "${DEB_ROOT}/opt/${PACKAGE_NAME}/${APP_BINARY_NAME}"
cp -f "dist/${UPDATER_BINARY_NAME}" "${DEB_ROOT}/opt/${PACKAGE_NAME}/${UPDATER_BINARY_NAME}"
cp -f "README.md" "${DEB_ROOT}/opt/${PACKAGE_NAME}/README.md"
cp -f "PROJECT_PLAN.md" "${DEB_ROOT}/opt/${PACKAGE_NAME}/PROJECT_PLAN.md"
cp -f "update_manifest.example.json" "${DEB_ROOT}/opt/${PACKAGE_NAME}/update_manifest.example.json"
cp -f "LICENSE" "${DEB_ROOT}/opt/${PACKAGE_NAME}/LICENSE"
cp -f "LICENSE" "${DEB_ROOT}/usr/share/doc/${PACKAGE_NAME}/copyright"
cp -f "$ICON_OUTPUT" "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/${PACKAGE_NAME}.png"
cp -f "$ICON_OUTPUT" "${DEB_ROOT}/usr/share/pixmaps/${PACKAGE_NAME}.png"
cp -f "$APPDATA_TEMPLATE" "${DEB_ROOT}/usr/share/metainfo/${APPDATA_OUTPUT_NAME}"
render_desktop_file "format-foundry" "${DEB_ROOT}/usr/share/applications/${DESKTOP_ID}"
cat > "${DEB_ROOT}/usr/bin/format-foundry" <<'EOF'
#!/bin/sh
exec /opt/format-foundry/FormatFoundry "$@"
EOF
cat > "${DEB_ROOT}/usr/bin/format-foundry-updater" <<'EOF'
#!/bin/sh
exec /opt/format-foundry/FormatFoundry_Updater "$@"
EOF
chmod 755 \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/${APP_BINARY_NAME}" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/${UPDATER_BINARY_NAME}" \
  "${DEB_ROOT}/usr/bin/format-foundry" \
  "${DEB_ROOT}/usr/bin/format-foundry-updater"
cat > "${DEB_ROOT}/DEBIAN/control" <<EOF
Package: ${PACKAGE_NAME}
Version: ${DEBIAN_VERSION}
Section: utils
Priority: optional
Architecture: ${DEB_ARCH}
Maintainer: Pugmaster04 <noreply@users.noreply.github.com>
Depends: xdg-utils
Suggests: ffmpeg, pandoc, libreoffice, p7zip-full, imagemagick, aria2
Description: ${APP_NAME}
 Modular desktop utility for conversion, extraction, archives, media workflows,
 storage analysis, and aria2-based downloads.
EOF
find "${DEB_ROOT}" -type d -exec chmod 755 {} +
chmod 644 \
  "${DEB_ROOT}/DEBIAN/control" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/README.md" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/PROJECT_PLAN.md" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/update_manifest.example.json" \
  "${DEB_ROOT}/opt/${PACKAGE_NAME}/LICENSE" \
  "${DEB_ROOT}/usr/share/applications/${DESKTOP_ID}" \
  "${DEB_ROOT}/usr/share/doc/${PACKAGE_NAME}/copyright" \
  "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/${PACKAGE_NAME}.png" \
  "${DEB_ROOT}/usr/share/pixmaps/${PACKAGE_NAME}.png" \
  "${DEB_ROOT}/usr/share/metainfo/${APPDATA_OUTPUT_NAME}"
dpkg-deb --build --root-owner-group "$DEB_ROOT" "$DEB_PACKAGE"
appstreamcli validate --pedantic --no-net "${DEB_ROOT}/usr/share/metainfo/${APPDATA_OUTPUT_NAME}"

echo "[7/8] Creating AppImage..."
download_appimagetool
mkdir -p \
  "${APPDIR_ROOT}/usr/bin" \
  "${APPDIR_ROOT}/usr/share/applications" \
  "${APPDIR_ROOT}/usr/share/doc/${PACKAGE_NAME}" \
  "${APPDIR_ROOT}/usr/share/icons/hicolor/256x256/apps" \
  "${APPDIR_ROOT}/usr/share/metainfo"
cp -f "dist/${APP_BINARY_NAME}" "${APPDIR_ROOT}/usr/bin/${APP_BINARY_NAME}"
cp -f "dist/${UPDATER_BINARY_NAME}" "${APPDIR_ROOT}/usr/bin/${UPDATER_BINARY_NAME}"
cp -f "README.md" "${APPDIR_ROOT}/usr/bin/README.md"
cp -f "PROJECT_PLAN.md" "${APPDIR_ROOT}/usr/bin/PROJECT_PLAN.md"
cp -f "update_manifest.example.json" "${APPDIR_ROOT}/usr/bin/update_manifest.example.json"
cp -f "LICENSE" "${APPDIR_ROOT}/usr/bin/LICENSE"
cp -f "LICENSE" "${APPDIR_ROOT}/usr/share/doc/${PACKAGE_NAME}/copyright"
sed 's/\r$//' "$APP_RUN_TEMPLATE" > "${APPDIR_ROOT}/AppRun"
cp -f "$ICON_OUTPUT" "${APPDIR_ROOT}/${PACKAGE_NAME}.png"
cp -f "$ICON_OUTPUT" "${APPDIR_ROOT}/.DirIcon"
cp -f "$ICON_OUTPUT" "${APPDIR_ROOT}/usr/share/icons/hicolor/256x256/apps/${PACKAGE_NAME}.png"
cp -f "$APPDATA_TEMPLATE" "${APPDIR_ROOT}/usr/share/metainfo/${APPDATA_OUTPUT_NAME}"
render_desktop_file "${APP_BINARY_NAME}" "${APPDIR_ROOT}/${DESKTOP_ID}"
cp -f "${APPDIR_ROOT}/${DESKTOP_ID}" "${APPDIR_ROOT}/usr/share/applications/${DESKTOP_ID}"
chmod 755 "${APPDIR_ROOT}/AppRun" "${APPDIR_ROOT}/usr/bin/${APP_BINARY_NAME}" "${APPDIR_ROOT}/usr/bin/${UPDATER_BINARY_NAME}"
appstreamcli validate --pedantic --no-net "${APPDIR_ROOT}/usr/share/metainfo/${APPDATA_OUTPUT_NAME}"
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE_TOOL" "$APPDIR_ROOT" "$APPIMAGE_PACKAGE"
chmod +x "$APPIMAGE_PACKAGE"

echo "[8/8] Validating install surface..."
"${PYTHON_BIN}" tools/validate_install_surface.py \
  --readme README.md \
  --artifacts release_bins \
  --required-asset "format-foundry_${PACKAGE_VERSION}_${DEB_ARCH}.deb" \
  --required-asset "FormatFoundry_linux_${PACKAGE_VERSION}_${ARCH}.AppImage"

(
  cd release_bins
  sha256sum \
    "${TAR_BASENAME}.tar.gz" \
    "${PACKAGE_NAME}_${PACKAGE_VERSION}_${DEB_ARCH}.deb" \
    "${APP_BINARY_NAME}_linux_${PACKAGE_VERSION}_${ARCH}.AppImage" \
    > "SHA256SUMS-linux"
  cp -f "SHA256SUMS-linux" "SHA256SUMS"
)

echo "Done."
echo "App binary:      $ROOT/dist/${APP_BINARY_NAME}"
echo "Updater binary:  $ROOT/dist/${UPDATER_BINARY_NAME}"
echo "Staged output:   $ROOT/release_bins"
echo "Linux package:   $ROOT/$TAR_PACKAGE"
echo "Debian package:  $ROOT/$DEB_PACKAGE"
echo "AppImage:        $ROOT/$APPIMAGE_PACKAGE"
echo "Checksums:       $ROOT/release_bins/SHA256SUMS-linux"
echo "Local alias:     $ROOT/release_bins/SHA256SUMS"

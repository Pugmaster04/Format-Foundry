#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$("${ROOT}/.venv/bin/python" "${ROOT}/tools/extract_app_version.py")"
DEB="${ROOT}/release_bins/format-foundry_${VERSION}_amd64.deb"
APPIMAGE="${ROOT}/release_bins/FormatFoundry_linux_${VERSION}_x86_64.AppImage"
TARBALL="${ROOT}/release_bins/FormatFoundry_linux_${VERSION}_x86_64.tar.gz"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/foundry-package-check.XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/home" "$WORK/config" "$WORK/cache"
export HOME="$WORK/home" XDG_CONFIG_HOME="$WORK/config" XDG_CACHE_HOME="$WORK/cache"

(cd "${ROOT}/release_bins" && sha256sum --check SHA256SUMS-linux)
DEB_VERSION="$(dpkg-deb -f "$DEB" Version)"
EXPECTED_DEB_VERSION="1:${VERSION/-beta/~beta}"
dpkg --compare-versions "$DEB_VERSION" eq "$EXPECTED_DEB_VERSION"
dpkg --compare-versions "$DEB_VERSION" gt 1.8.17
dpkg --compare-versions "${DEB_VERSION}" lt "1:${VERSION/-beta/}"
test "$(dpkg-deb -f "$DEB" Installed-Size)" -gt 0
test -n "$(dpkg-deb -f "$DEB" Homepage)"
dpkg-deb -f "$DEB" Package Version Installed-Size Homepage Depends
dpkg-deb --extract "$DEB" "$WORK/deb"
cd "$WORK"
for binary in FormatFoundry FormatFoundry_Updater; do
  "$WORK/deb/opt/format-foundry/$binary" --version
  "$WORK/deb/opt/format-foundry/$binary" --smoke-test
  ldd "$WORK/deb/opt/format-foundry/$binary" > "$WORK/ldd.txt"
  if grep -q 'not found' "$WORK/ldd.txt"; then
    cat "$WORK/ldd.txt"
    exit 1
  fi
done
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE" --version
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE" --smoke-test
tar -xzf "$TARBALL" -C "$WORK"
"$WORK/FormatFoundry_linux_${VERSION}_x86_64/FormatFoundry" --smoke-test
echo "Linux package checks passed outside the source tree. No package was installed."

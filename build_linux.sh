#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "[1/4] Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "[2/4] Building app binary..."
python3 -m PyInstaller --noconfirm --clean UniversalConversionHub_HCB.spec

echo "[3/4] Building updater binary..."
python3 -m PyInstaller --noconfirm --clean UniversalConversionHub_HCB_Updater.spec

echo "[4/4] Staging binaries..."
mkdir -p release_bins
if [[ -f "dist/UniversalConversionHub_HCB" ]]; then
  cp -f "dist/UniversalConversionHub_HCB" "release_bins/UniversalConversionHub_HCB"
fi
if [[ -f "dist/UniversalConversionHub_HCB_Updater" ]]; then
  cp -f "dist/UniversalConversionHub_HCB_Updater" "release_bins/UniversalConversionHub_HCB_Updater"
fi

echo "Done."
echo "App binary:      $ROOT/dist/UniversalConversionHub_HCB"
echo "Updater binary:  $ROOT/dist/UniversalConversionHub_HCB_Updater"
echo "Staged output:   $ROOT/release_bins"

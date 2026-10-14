#!/usr/bin/env bash
# Installs Godot export templates for Linux and Windows only (the full .tpz is ~1.2 GB; we keep ~200 MB).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/scripts/godot-version.txt")"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/${VERSION}.stable"

if [ -f "$DEST/linux_release.x86_64" ] && [ -f "$DEST/windows_release_x86_64.exe" ]; then
  echo "Export templates already installed in $DEST" >&2
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
url="https://github.com/godotengine/godot/releases/download/${VERSION}-stable/Godot_v${VERSION}-stable_export_templates.tpz"
echo "Downloading export templates ${VERSION}..." >&2
# Large download: resume on dropped connections instead of starting over.
for attempt in 1 2 3 4 5 6; do
  if curl -fsSL --retry 3 --retry-all-errors -C - -o "$tmp/templates.tpz" "$url"; then
    break
  fi
  [ "$attempt" -eq 6 ] && { echo "Template download failed" >&2; exit 1; }
  sleep $((attempt * 2))
done
mkdir -p "$DEST"
unzip -o -j -q "$tmp/templates.tpz" \
  'templates/version.txt' \
  'templates/linux_debug.x86_64' 'templates/linux_release.x86_64' \
  'templates/windows_debug_x86_64.exe' 'templates/windows_release_x86_64.exe' \
  -d "$DEST"
echo "$DEST"

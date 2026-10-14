#!/usr/bin/env bash
# Downloads the pinned Godot editor (Linux x86_64) into .tools/godot/ and links it as `godot`.
# Used by cloud sessions and CI. On your own machine, install Godot normally and set GODOT=/path/to/godot.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/scripts/godot-version.txt")"
DEST="$ROOT/.tools/godot"
BIN="$DEST/Godot_v${VERSION}-stable_linux.x86_64"

if [ ! -x "$BIN" ]; then
  mkdir -p "$DEST"
  url="https://github.com/godotengine/godot/releases/download/${VERSION}-stable/Godot_v${VERSION}-stable_linux.x86_64.zip"
  echo "Downloading Godot ${VERSION}..." >&2
  curl -fsSL --retry 4 --retry-all-errors -C - -o "$DEST/godot.zip" "$url"
  unzip -o -q "$DEST/godot.zip" -d "$DEST"
  rm -f "$DEST/godot.zip"
  chmod +x "$BIN"
fi

ln -sf "$BIN" "$DEST/godot"
# Put `godot` on PATH when we can (cloud containers and CI run as a user that can write here).
for dir in /usr/local/bin "$HOME/.local/bin"; do
  if [ -d "$dir" ] && [ -w "$dir" ]; then
    ln -sf "$BIN" "$dir/godot"
    break
  fi
done

echo "$BIN"

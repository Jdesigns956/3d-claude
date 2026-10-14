#!/usr/bin/env bash
# Installs headless Blender (the `bpy` Python module, pinned) plus Pillow into .tools/venv. Needs Python 3.13.
# Nothing here needs a GPU or a display. Prints the venv's python path. Works in Git Bash on Windows too.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/scripts/bpy-version.txt")"
VENV="$ROOT/.tools/venv"

find_python() {
  for candidate in "$VENV/bin/python" "$VENV/Scripts/python.exe"; do
    [ -x "$candidate" ] && { echo "$candidate"; return; }
  done
}

PY="$(find_python)"
if [ -z "$PY" ]; then
  python3 -m venv "$VENV" 2>/dev/null || python -m venv "$VENV"
  PY="$(find_python)"
fi
if ! "$PY" -c "import bpy, sys; sys.exit(0 if bpy.app.version_string.startswith('${VERSION%.*}') else 1)" 2>/dev/null; then
  echo "Installing bpy ${VERSION} (about 400 MB)..." >&2
  "$PY" -m pip install --quiet --disable-pip-version-check "bpy==${VERSION}" pillow >&2
fi
echo "$PY"

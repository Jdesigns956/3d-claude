#!/bin/bash
# PostToolUse (Edit|Write): parse-check edited GDScript right away, and flag the game as changed
# so the Stop gate runs the full check before Claude calls the work done.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

file="$(python3 -c 'import json, sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')"
case "$file" in
  "$ROOT"/game/*) ;;
  *) exit 0 ;;
esac
touch "$ROOT/.claude/.game-dirty"

case "$file" in
  *.gd) ;;
  *) exit 0 ;;
esac
out="$("$ROOT/scripts/check.sh" --file "$file" 2>&1)"
if [ $? -eq 1 ]; then
  echo "$out" >&2
  exit 2
fi
exit 0

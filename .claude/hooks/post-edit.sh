#!/bin/bash
# PostToolUse (Edit|Write): when a piece, the studio kit or the pipeline changes, check it right away
# (syntax; for pieces, also build the scene and render one tiny frame through the QA checks),
# and flag the work as changed so the Stop gate runs the full check before Claude says it's done.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

file="$(python3 -c 'import json, sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')"
case "$file" in
  "$ROOT"/pieces/*.py|"$ROOT"/studio/*.py|"$ROOT"/pipeline/*.py|"$ROOT"/pipeline/tests/*.py) ;;
  *) exit 0 ;;
esac
touch "$ROOT/.claude/.studio-dirty"

out="$("$ROOT/scripts/check.sh" --file "$file" 2>&1)"
if [ $? -eq 1 ]; then
  echo "$out" >&2
  exit 2
fi
exit 0

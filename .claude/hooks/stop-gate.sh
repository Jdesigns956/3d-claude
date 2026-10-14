#!/bin/bash
# Stop: if Claude edited the game this session, it can't finish until scripts/check.sh passes
# (import, parse, smoke test). Gives up after 3 blocked attempts and hands back to the human.
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
MARKER="$ROOT/.claude/.game-dirty"
ATTEMPTS="$ROOT/.claude/.stop-gate-attempts"

[ -f "$MARKER" ] || exit 0

out="$("$ROOT/scripts/check.sh" 2>&1)"
code=$?
if [ $code -eq 0 ] || [ $code -eq 3 ]; then  # passing, or no Godot on this machine
  rm -f "$MARKER" "$ATTEMPTS"
  exit 0
fi

n=$(( $(cat "$ATTEMPTS" 2>/dev/null || echo 0) + 1 ))
if [ "$n" -gt 3 ]; then
  rm -f "$ATTEMPTS"
  echo '{"systemMessage": "Stop gate: the game check is still failing after 3 fix attempts. Run scripts/check.sh to see why."}'
  exit 0
fi
echo "$n" > "$ATTEMPTS"
{
  echo "Not done yet: the game's headless check fails (attempt $n/3). Fix it, then finish."
  echo "$out" | grep -vE '^(== |PASS )' | tail -25
} >&2
exit 2

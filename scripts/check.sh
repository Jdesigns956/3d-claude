#!/usr/bin/env bash
# Headless health check for the Godot project.
#   scripts/check.sh                 import, parse every script, run tests/smoke_test.gd
#   scripts/check.sh --file <path>   parse one .gd file only (what the post-edit hook runs)
# Exit 0 = healthy, 1 = errors (summary on stderr), 3 = Godot not installed.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/godot-env.sh"

if [ -z "${GODOT:-}" ]; then
  echo "check.sh: Godot not found. Set GODOT=/path/to/godot or run scripts/install-godot.sh" >&2
  exit 3
fi

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

parse_one() {  # $1 = res:// path
  "$GODOT" --headless --path "$GAME" --check-only -s "$1" >"$LOG" 2>&1
}

if [ "${1:-}" = "--file" ]; then
  file="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
  case "$file" in
    "$GAME"/*.gd) ;;
    *) exit 0 ;;
  esac
  res="res://${file#"$GAME"/}"
  if ! parse_one "$res"; then
    # A new class_name elsewhere may not be in the class cache yet; refresh it once and retry.
    "$GODOT" --headless --path "$GAME" --import >/dev/null 2>&1
    if ! parse_one "$res"; then
      echo "Parse errors in $res:" >&2
      godot_errors "$LOG" >&2
      exit 1
    fi
  fi
  exit 0
fi

status=0

echo "== import" >&2
"$GODOT" --headless --path "$GAME" --import >"$LOG" 2>&1
if grep -qE "SCRIPT ERROR|^ERROR:" "$LOG"; then
  echo "Import errors:" >&2
  godot_errors "$LOG" >&2
  status=1
fi

echo "== parse" >&2
while IFS= read -r f; do
  res="res://${f#"$GAME"/}"
  if ! parse_one "$res"; then
    echo "Parse errors in $res:" >&2
    godot_errors "$LOG" >&2
    status=1
  fi
done < <(find "$GAME" -name '*.gd' -not -path '*/.godot/*' -not -path '*/addons/*' | sort)

echo "== smoke test" >&2
"$GODOT" --headless --path "$GAME" -s res://tests/smoke_test.gd >"$LOG" 2>&1
smoke=$?
grep -E "^(PASS|FAIL|SMOKE)" "$LOG" >&2
if [ $smoke -ne 0 ] || grep -qE "SCRIPT ERROR|^ERROR:" "$LOG"; then
  echo "Smoke test errors:" >&2
  godot_errors "$LOG" >&2
  status=1
fi

[ $status -eq 0 ] && echo "check.sh: OK" >&2 || echo "check.sh: FAILED" >&2
exit $status

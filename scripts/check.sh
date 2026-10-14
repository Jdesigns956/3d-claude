#!/usr/bin/env bash
# Headless health check for the studio.
#   scripts/check.sh                 compile everything, pipeline tests, then build + QA every piece (tiny render)
#   scripts/check.sh --file <path>   what the post-edit hook runs: compile that file; for pieces, build + QA it;
#                                    for studio/*.py, check every piece (a kit change can break any of them)
# Exit 0 = healthy, 1 = errors (summary on stderr), 3 = Blender not installed (run scripts/install-blender.sh).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${STUDIO_PY:-$ROOT/.tools/venv/bin/python}"
[ -x "$PY" ] || PY="$ROOT/.tools/venv/Scripts/python.exe"
if [ ! -x "$PY" ] || ! "$PY" -c "import bpy" 2>/dev/null; then
  echo "check.sh: Blender not installed. Run scripts/install-blender.sh" >&2
  exit 3
fi

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT
status=0

compile() {  # $@ = files
  if ! "$PY" -m py_compile "$@" >"$LOG" 2>&1; then
    echo "Syntax errors:" >&2
    grep -vE '^\s*$' "$LOG" | tail -n 12 >&2
    return 1
  fi
}

check_piece() {  # $1 = piece name
  if ! (cd "$ROOT" && "$PY" studio/run.py "$1" --mode check >"$LOG" 2>&1); then
    echo "Piece '$1' failed its check:" >&2
    grep -E "^\s+(FAIL|WARN)|Error|error|Traceback|File \"" "$LOG" | grep -v "CUEW" | tail -n 14 >&2
    return 1
  fi
}

all_pieces() { find "$ROOT/pieces" -maxdepth 1 -name '*.py' -printf '%f\n' 2>/dev/null | sed 's/\.py$//' | sort; }

if [ "${1:-}" = "--file" ]; then
  file="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
  case "$file" in
    "$ROOT"/pieces/*.py)  compile "$file" || exit 1; check_piece "$(basename "$file" .py)" || exit 1 ;;
    "$ROOT"/studio/*.py)  compile "$file" || exit 1
                          for p in $(all_pieces); do check_piece "$p" || status=1; done; exit $status ;;
    "$ROOT"/pipeline/*.py|"$ROOT"/pipeline/tests/*.py) compile "$file" || exit 1 ;;
  esac
  exit 0
fi

echo "== compile" >&2
compile "$ROOT"/studio/*.py "$ROOT"/pieces/*.py "$ROOT"/pipeline/*.py "$ROOT"/pipeline/tests/*.py || status=1

echo "== pipeline tests" >&2
if ! (cd "$ROOT" && python3 -m unittest discover -s pipeline/tests >"$LOG" 2>&1); then
  echo "Pipeline tests failed:" >&2
  tail -n 20 "$LOG" >&2
  status=1
fi

echo "== pieces" >&2
for p in $(all_pieces); do
  if check_piece "$p"; then echo "ok  $p" >&2; else status=1; fi
done

[ $status -eq 0 ] && echo "check.sh: OK" >&2 || echo "check.sh: FAILED" >&2
exit $status

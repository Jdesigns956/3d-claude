# Sourced by the other scripts. Finds the Godot binary: $GODOT, then `godot` on PATH, then .tools/.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAME="$ROOT/game"
if [ -z "${GODOT:-}" ]; then
  if command -v godot >/dev/null 2>&1; then
    GODOT="$(command -v godot)"
  elif [ -x "$ROOT/.tools/godot/godot" ]; then
    GODOT="$ROOT/.tools/godot/godot"
  fi
fi

# Collapse Godot's error output to one line per unique error with its location.
godot_errors() {
  awk '
    /SCRIPT ERROR:|^ERROR:/ { msg=$0; sub(/^ */, "", msg); getline nxt; sub(/^ */, "", nxt);
                              line=msg; if (nxt ~ /^at:/) line=line "  (" nxt ")";
                              if (!seen[line]++) print line; next }
    /^FAIL / { print }
  ' "$1" | head -n 20
}

#!/bin/bash
# SessionStart (cloud sessions only): install the pinned Godot so the hooks, smoke test and godot MCP work.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
bin="$(scripts/install-godot.sh)"
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export GODOT=\"$bin\"" >> "$CLAUDE_ENV_FILE"
fi
# Build the import cache once so the first check is fast.
"$bin" --headless --path game --import >/dev/null 2>&1 || true
# Pre-fetch the godot MCP server so it starts without a download.
npm cache add @coding-solo/godot-mcp >/dev/null 2>&1 || true

echo "Godot $(cat scripts/godot-version.txt) ready. Run scripts/check.sh to verify the game."

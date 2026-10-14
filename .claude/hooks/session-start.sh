#!/bin/bash
# SessionStart (cloud sessions only): install headless Blender (the pinned bpy module) so renders and checks work.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
py="$(scripts/install-blender.sh)"
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export STUDIO_PY=\"$py\"" >> "$CLAUDE_ENV_FILE"
fi
echo "Blender $("$py" -c 'import bpy; print(bpy.app.version_string)' 2>/dev/null) ready. Run scripts/check.sh to verify the studio."

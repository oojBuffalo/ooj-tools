#!/usr/bin/env bash
# Claude Code PreToolUse hook for Edit|Write|MultiEdit.
# Deterministically injects the AGENTS.md chain for the path being edited, so
# the relevant local contracts are ALWAYS in context - the model never has to
# remember to read them. This is job J1 (load the right docs), mechanised.
#
# Wire in .claude/settings.json under hooks.PreToolUse (see settings.snippet.json).
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
DOX="$ROOT/dox/bin/dox"
[ -x "$DOX" ] || DOX="$ROOT/bin/dox"   # fallback if dox lives at repo root

input="$(cat)"
# Extract the target path from the tool input JSON (file_path for Edit/Write).
path="$(printf '%s' "$input" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)"
[ -n "$path" ] || exit 0
[ -x "$DOX" ] || exit 0

ctx="$(python3 "$DOX" context "$path" 2>/dev/null || true)"
[ -n "$ctx" ] || exit 0

# Feed the chain back as additional context for this tool call.
python3 - "$ctx" <<'PY'
import json, sys
ctx = sys.argv[1]
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": "Local AGENTS.md contracts for this path (dox):\n\n" + ctx,
    }
}))
PY

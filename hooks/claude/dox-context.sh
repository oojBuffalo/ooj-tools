#!/usr/bin/env bash
# Claude Code PreToolUse hook for Edit|Write|MultiEdit.
# Deterministically injects the AGENTS.md chain for the path being edited, so
# the relevant local contracts are ALWAYS in context - the model never has to
# remember to read them. This is job J1 (load the right docs), mechanised.
#
# Wire in .claude/settings.json under hooks.PreToolUse (see settings.snippet.json).
# Node-only: the engine and the JSON munging both run on the Node the harness
# already has - no extra runtime dependency.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

DOX=()
if command -v dox >/dev/null 2>&1; then
  DOX=(dox)
else
  for c in "$ROOT/dox/dist/cli.js" "$ROOT/dist/cli.js" "$ROOT/node_modules/@dox/cli/dist/cli.js"; do
    [ -f "$c" ] && { DOX=(node "$c"); break; }
  done
fi
[ ${#DOX[@]} -gt 0 ] || exit 0

input="$(cat)"
# Extract the target path from the tool input JSON (file_path for Edit/Write).
path="$(printf '%s' "$input" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{process.stdout.write((JSON.parse(d).tool_input||{}).file_path||"")}catch{}})' 2>/dev/null || true)"
[ -n "$path" ] || exit 0

ctx="$("${DOX[@]}" context "$path" 2>/dev/null || true)"
[ -n "$ctx" ] || exit 0

# Feed the chain back as additional context for this tool call.
node -e 'const ctx=process.argv[1];process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:"Local AGENTS.md contracts for this path (dox):\n\n"+ctx}}))' "$ctx"

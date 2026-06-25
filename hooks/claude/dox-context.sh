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

# Target: the user's repo, where the AGENTS.md tree lives. The engine operates
# on this (passed via `dox -C`), regardless of where the engine itself lives.
TARGET="${CLAUDE_PROJECT_DIR:-$PWD}"

# Opt-in guard: only act in repos that use dox (a .dox.json, written by `dox
# init`). Without this a globally-installed plugin would inject nothing / block
# in every unrelated repo. The CLI stays strict; this policy lives in the hook.
[ -f "$TARGET/.dox.json" ] || exit 0

# Engine: prefer an installed `dox` bin, else this plugin's bundled build
# (CLAUDE_PLUGIN_ROOT, set when run as a Claude Code plugin), else a build
# vendored inside the target repo (legacy / non-plugin install).
DOX=()
if command -v dox >/dev/null 2>&1; then
  DOX=(dox)
else
  for c in \
    "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/dist/cli.js}" \
    "$TARGET/dox/dist/cli.js" \
    "$TARGET/dist/cli.js" \
    "$TARGET/node_modules/@dox/cli/dist/cli.js"; do
    [ -n "$c" ] && [ -f "$c" ] && { DOX=(node "$c"); break; }
  done
fi
[ ${#DOX[@]} -gt 0 ] || exit 0

input="$(cat)"
# Extract the target path from the tool input JSON (file_path for Edit/Write).
path="$(printf '%s' "$input" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{process.stdout.write((JSON.parse(d).tool_input||{}).file_path||"")}catch{}})' 2>/dev/null || true)"
[ -n "$path" ] || exit 0

ctx="$("${DOX[@]}" -C "$TARGET" context "$path" 2>/dev/null || true)"
[ -n "$ctx" ] || exit 0

# Feed the chain back as additional context for this tool call.
node -e 'const ctx=process.argv[1];process.stdout.write(JSON.stringify({hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:"Local AGENTS.md contracts for this path (dox):\n\n"+ctx}}))' "$ctx"

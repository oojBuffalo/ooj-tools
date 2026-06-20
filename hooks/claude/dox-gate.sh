#!/usr/bin/env bash
# Claude Code Stop hook.
# Before the agent is allowed to finish, deterministically (1) regenerate the
# index blocks - always safe, no model judgement - and (2) check for hard drift
# (missing docs, dangling refs). If found, block with exit 2 so the message is
# fed back to the model and it must address the docs before stopping.
# Prose-drift is surfaced as a non-blocking reminder.
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

"${DOX[@]}" sync >/dev/null 2>&1 || true

out="$("${DOX[@]}" check 2>&1 || true)"
if printf '%s' "$out" | grep -q 'dox: ERROR'; then
  {
    echo "dox: documentation drift must be resolved before finishing."
    printf '%s\n' "$out" | grep 'dox: ERROR'
    echo "Fix: add the missing AGENTS.md / correct the dangling links, then continue."
  } >&2
  exit 2
fi

# Non-blocking prose reminder.
printf '%s\n' "$out" | grep 'dox: warn' >&2 || true
exit 0

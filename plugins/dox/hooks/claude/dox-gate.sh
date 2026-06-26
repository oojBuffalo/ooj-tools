#!/usr/bin/env bash
# Claude Code Stop hook.
# Before the agent is allowed to finish, deterministically (1) regenerate the
# index blocks - always safe, no model judgement - and (2) check for hard drift
# (missing docs, dangling refs). If found, block with exit 2 so the message is
# fed back to the model and it must address the docs before stopping.
# Prose-drift is surfaced as a non-blocking reminder.
set -euo pipefail

# Target: the user's repo, where the AGENTS.md tree lives. The engine operates
# on this (passed via `dox -C`), regardless of where the engine itself lives.
TARGET="${CLAUDE_PROJECT_DIR:-$PWD}"

# Opt-in guard: only act in repos that use dox (a .dox.json, written by `dox
# init`). Without this a globally-installed plugin would block Stop in every
# unrelated repo. The CLI stays strict; this policy lives in the hook.
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

"${DOX[@]}" -C "$TARGET" sync >/dev/null 2>&1 || true

out="$("${DOX[@]}" -C "$TARGET" check 2>&1 || true)"
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

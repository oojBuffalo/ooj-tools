#!/bin/bash
# SessionStart nudge: offer a profile pick in unconfigured git repos.
# Every non-nudge path exits 0 silently -- this hook must never block a session.

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0
[ -e "$root/.claude/plugin-configure.json" ] && exit 0
settings="$root/.claude/settings.local.json"
if [ -f "$settings" ] && grep -q '"skillOverrides"' "$settings"; then
  exit 0
fi

cat <<JSON
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "plugin-configure: this repo has no skill/plugin profile applied. After handling the user's immediate request (or right away if there is none), invoke the plugin-configure:configure command via the Skill tool to offer a one-card profile pick. If the user declines, silence this nudge permanently for this repo by running: python3 \\"${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py\\" --skip"}}
JSON
exit 0

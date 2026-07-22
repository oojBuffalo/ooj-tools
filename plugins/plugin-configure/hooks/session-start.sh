#!/bin/bash
# SessionStart nudge: offer a profile pick in unconfigured git repos.
# Every path exits 0 -- this hook must never block a session.

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0
[ -e "$root/.claude/plugin-configure.json" ] && exit 0
settings="$root/.claude/settings.local.json"
if [ -f "$settings" ] && grep -q '"skillOverrides"' "$settings"; then
  exit 0
fi

# Build the nudge with real JSON escaping: CLAUDE_PLUGIN_ROOT can contain
# characters (quotes, backslashes) that would corrupt a hand-interpolated
# string. The quoted heredoc keeps the shell out of the script entirely; the
# env var is read inside python instead.
python3 - <<'PY' 2>/dev/null
import json
import os
import shlex

script = os.environ.get("CLAUDE_PLUGIN_ROOT", "") + "/scripts/apply_profile.py"
context = (
    "plugin-configure: this repo has no skill/plugin profile applied. After "
    "handling the user's immediate request (or right away if there is none), "
    "invoke the plugin-configure:configure command via the Skill tool to "
    "offer a one-card profile pick. If the user declines, silence this nudge "
    "permanently for this repo by running: "
    "python3 " + shlex.quote(script) + " --skip"
)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": context,
}}))
PY
exit 0

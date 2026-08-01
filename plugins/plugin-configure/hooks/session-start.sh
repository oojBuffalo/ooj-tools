#!/bin/bash
# SessionStart nudge: offer a profile pick in unconfigured git repos.
# Every path exits 0 -- this hook must never block a session.

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0
[ -e "$root/.claude/plugin-configure.json" ] && exit 0

# Already-curated repos are silent: a real top-level skillOverrides key in
# either the local or the checked-in project settings counts. This must be a
# JSON key check, not a grep -- the bare token can appear inside string
# values (e.g. a permissions rule) in a repo that is not configured at all.
python3 - "$root/.claude/settings.local.json" "$root/.claude/settings.json" <<'PY' 2>/dev/null && exit 0
import json
import os
import sys

for path in sys.argv[1:]:
    # isfile() rejects FIFOs and other specials whose open() could block --
    # this hook must never stall a session start.
    if not os.path.isfile(path):
        continue
    try:
        # utf-8-sig tolerates a BOM (common from Windows editors) and reads
        # plain UTF-8 unchanged.
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except Exception:
        # Any per-file failure (corrupt JSON, RecursionError from absurd
        # nesting, unreadable file) must not mask a valid key in the other.
        continue
    if isinstance(doc, dict) and "skillOverrides" in doc:
        sys.exit(0)
sys.exit(1)
PY

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

---
description: Apply a skill/plugin profile to this repo's .claude/settings.local.json (or re-apply / skip)
---

Apply a curated skill/plugin profile to the current repo's local settings.
Follow these steps exactly:

1. Run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" --bootstrap-only`
   It prints one `name: description` line per available profile (bootstrapping
   `~/.claude/plugin-configure/profiles.json` with starter profiles on first
   run).

2. Present ONE AskUserQuestion card asking which profile to apply: one option
   per profile (label = profile name, description = its description line), max
   4 options. If there are more than 4 profiles, prefer `general-dev`,
   `minimal`, `web-dev`, `data-ml` and mention the rest in the question text
   (reachable via "Other"). The automatic "Other" option doubles as the skip
   path — mention that in the question text.

3. Act on the answer:
   - A profile name (picked or typed): run
     `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" <profile>`
   - "Other" with skip-like text, a dismissal, or an explicit decline: run
     `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" --skip`

4. Relay the script's summary (skills turned off, plugins disabled/enabled,
   file paths) and remind the user the new settings take effect from the next
   Claude Code session in this directory — the current session keeps its
   already-loaded skills. Profiles can be edited any time at
   `~/.claude/plugin-configure/profiles.json`; re-running this command
   re-applies over the previous choice.

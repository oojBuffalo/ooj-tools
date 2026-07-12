---
description: Show effective Claude Code transcript verbosity and archive location
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcripts.py" --agent claude --data-dir "${CLAUDE_PLUGIN_DATA}" status --cwd "$PWD"` and present its output without modification.

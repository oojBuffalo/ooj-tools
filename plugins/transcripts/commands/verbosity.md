---
description: Set Claude Code transcript verbosity globally or for the current repository
argument-hint: '<conversation|activity|full|reset> [--global|--repo]'
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Parse `$ARGUMENTS` only as the supported level and scope tokens. If scope is omitted, use `--repo` inside Git and `--global` otherwise. Run the matching command:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcripts.py" --agent claude --data-dir "${CLAUDE_PLUGIN_DATA}" verbosity <level> <scope> --cwd "$PWD"`

Reject all other tokens. Present the command output without modification.

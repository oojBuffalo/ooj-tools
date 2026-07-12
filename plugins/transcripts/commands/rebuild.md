---
description: Rebuild Claude Code Markdown transcripts from available source JSONL
argument-hint: '[--current|--all]'
disable-model-invocation: true
allowed-tools: Bash(python3:*)
---

Accept only `--current` or `--all`; default to `--current`. Run:

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/transcripts.py" --agent claude --data-dir "${CLAUDE_PLUGIN_DATA}" rebuild <mode> --cwd "$PWD"`

Present the summary without modification.

---
name: transcripts
description: Configure or rebuild local Markdown session transcripts. In Codex, use when the user invokes $transcripts. In Claude Code, this is a compatibility control skill; prefer the focused status, verbosity, and rebuild commands.
---

# Transcripts

Determine the current agent. For Codex run:

```bash
python3 <plugin-root>/scripts/transcripts.py --agent codex <action> --cwd "$PWD"
```

For Claude Code run the same command with `--agent claude --data-dir "${CLAUDE_PLUGIN_DATA}"` and resolve the script through `${CLAUDE_PLUGIN_ROOT}`.

Supported actions are `status`, `verbosity conversation|activity|full --global|--repo`, `verbosity reset --repo`, and `rebuild --current|--all`. Default an omitted verbosity scope to repository inside Git and global otherwise. Default rebuild to current. Run exactly one validated command and relay its result.

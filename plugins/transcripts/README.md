# Transcripts

Worktree-safe Markdown transcript archives for Claude Code and Codex.

Claude Code commands:

```text
/transcripts:status
/transcripts:verbosity activity --repo
/transcripts:rebuild --current
```

Codex uses `$transcripts` with the same `conversation`, `activity`, and `full` levels.

Archives are written to the primary checkout under `.claude/sessions/` or `.codex/sessions/`. Linked-worktree and branch deletion do not remove them.

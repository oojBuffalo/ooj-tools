# ooj-tools

Plugins developed with agentic sensibilities in mind — tooling built for how
coding agents actually work.

This repo is a [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins).
Each plugin lives under `plugins/<name>/` with its own `.claude-plugin/plugin.json`;
the marketplace manifest at [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
lists them.

## Plugins

| Plugin | What it does |
|--------|--------------|
| [`dox`](plugins/dox/) | Deterministic AGENTS.md tree engine: injects the local AGENTS.md chain before edits (J1) and gates finishing on documentation drift (J3). |
| [`transcripts`](plugins/transcripts/) | Worktree-safe Claude Code and Codex transcript archives with configurable verbosity. |
| [`spec-to-tasks`](plugins/spec-to-tasks/) | Turn a PRD, spec, or MVP doc into a readable markdown task tree: parse into tasks, score complexity, and expand into subtasks — native skills, no MCP server or API keys. |

## Install

```
/plugin marketplace add /Users/claw/projects/ooj-tools
/plugin install dox@ooj-tools
/plugin install transcripts@ooj-tools
```

(Or point at the GitHub repo: `/plugin marketplace add oojBuffalo/ooj-tools`.)
Test a plugin in one session without installing — `--plugin-dir` loads a single
plugin directory, not the marketplace root, so point it at `plugins/<name>`
(repeat the flag per plugin to load more than one):

```
claude --plugin-dir /Users/claw/projects/ooj-tools/plugins/dox
```

For Codex, add this repository as a marketplace and install the same source:

```bash
codex plugin marketplace add /path/to/ooj-tools
codex plugin add transcripts@ooj-tools
```

## Adding a plugin

1. Create `plugins/<name>/` with a `.claude-plugin/plugin.json` (and whatever
   components it needs — `commands/`, `agents/`, `skills/`, `hooks/`).
2. Add an entry to `.claude-plugin/marketplace.json` with
   `"source": "./plugins/<name>"`.

If the plugin wants dox to maintain its own AGENTS.md tree, drop a `.dox.json`
in its root (`dox init`) — the repo's `git` pre-commit gate
([`plugins/dox/hooks/git/pre-commit`](plugins/dox/hooks/git/pre-commit)) checks
every `plugins/*/` that opts in.

## License

[MIT](LICENSE) for the collection; each plugin may carry its own license file
(see [`plugins/dox/LICENSE`](plugins/dox/LICENSE)) if it differs.

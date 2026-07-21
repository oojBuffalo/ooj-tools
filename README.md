# ooj-tools

Plugins developed with agentic sensibilities in mind — tooling built for how
coding agents actually work.

This repo is a [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins)
and a [Codex plugin marketplace](https://developers.openai.com/codex/plugins).
Each plugin lives under `plugins/<name>/` with its own `.claude-plugin/plugin.json`
(and, where it targets Codex, a `.codex-plugin/plugin.json`); the marketplace
manifests at [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)
(Claude Code) and [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json)
(Codex) list them.

## Plugins

| Plugin | What it does |
|--------|--------------|
| [`dox`](plugins/dox/) | Deterministic AGENTS.md tree engine: injects the local AGENTS.md chain before edits (J1) and gates finishing on documentation drift (J3). |
| [`transcripts`](plugins/transcripts/) | Worktree-safe Claude Code and Codex transcript archives with configurable verbosity. |
| [`spec-to-tasks`](plugins/spec-to-tasks/) | Turn a PRD, spec, or MVP doc into a readable markdown task tree: parse into tasks, score complexity, and expand into subtasks — native skills, no MCP server or API keys. |

## Install

```
/plugin marketplace add /path/to/ooj-tools
/plugin install dox@ooj-tools
/plugin install transcripts@ooj-tools
```

(Or point at the GitHub repo: `/plugin marketplace add oojBuffalo/ooj-tools`.)
Test a plugin in one session without installing — `--plugin-dir` loads a single
plugin directory, not the marketplace root, so point it at `plugins/<name>`
(repeat the flag per plugin to load more than one):

```
claude --plugin-dir /path/to/ooj-tools/plugins/dox
```

For Codex, add this repository as a marketplace and install the same source:

```bash
codex plugin marketplace add /path/to/ooj-tools
codex plugin add transcripts@ooj-tools
```

## Adding a plugin

1. Create `plugins/<name>/` with a `.claude-plugin/plugin.json` (and whatever
   components it needs — `commands/`, `agents/`, `skills/`, `hooks/`), following
   the [plugin structure reference](https://code.claude.com/docs/en/plugins-reference).
2. Add an entry to `.claude-plugin/marketplace.json` with
   `"source": "./plugins/<name>"` (schema:
   [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)).
3. To also offer it in Codex, add an entry to `.agents/plugins/marketplace.json`
   (schema: [build plugins](https://developers.openai.com/codex/plugins/build)).
   A `.codex-plugin/plugin.json` is optional — Codex falls back to reading
   `.claude-plugin/plugin.json`.

If the plugin wants dox to maintain its own AGENTS.md tree, drop a `.dox.json`
in its root (`dox init`) — the repo's `git` pre-commit gate
([`plugins/dox/hooks/git/pre-commit`](plugins/dox/hooks/git/pre-commit)) checks
every `plugins/*/` that opts in.

## Plugin-dev references

- Claude Code: [plugins overview](https://docs.claude.com/en/docs/claude-code/plugins) ·
  [plugin structure & manifest reference](https://code.claude.com/docs/en/plugins-reference) ·
  [marketplace schema](https://code.claude.com/docs/en/plugin-marketplaces) ·
  [hooks reference](https://code.claude.com/docs/en/hooks)
- Codex: [plugins overview](https://developers.openai.com/codex/plugins) ·
  [build plugins & marketplaces](https://developers.openai.com/codex/plugins/build) ·
  [hooks](https://developers.openai.com/codex/hooks) ·
  [skills](https://developers.openai.com/codex/skills) ·
  [openai/plugins](https://github.com/openai/plugins) (reference marketplace)

## License

[MIT](LICENSE) for the collection; each plugin may carry its own license file
(see [`plugins/dox/LICENSE`](plugins/dox/LICENSE)) if it differs.

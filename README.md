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

## Install

```
/plugin marketplace add /Users/claw/projects/ooj-tools
/plugin install dox@ooj-tools
```

(Or point at the GitHub repo: `/plugin marketplace add oojBuffalo/ooj-tools`.)
Test the whole collection in one session without installing:

```
claude --plugin-dir /Users/claw/projects/ooj-tools
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

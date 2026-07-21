# ooj-tools

Dual plugin marketplace: one repo serving both Claude Code and Codex. Each
plugin is a self-contained directory under `plugins/<name>/`.

## Layout

- `.claude-plugin/marketplace.json` — Claude Code marketplace manifest.
- `.agents/plugins/marketplace.json` — Codex marketplace manifest.
- `plugins/<name>/` — one plugin per directory; see
  [`plugins/AGENTS.md`](plugins/AGENTS.md) for the required structure.

## Commands

- Test a Python plugin: `python3 -m pytest plugins/<name>/tests/`
- Build and check dox: `cd plugins/dox && npm run build && node dist/cli.js check`
  — must print `dox: ok`.
- Try a plugin without installing: `claude --plugin-dir plugins/<name>`
  (one plugin directory per flag).
- Codex: `codex plugin marketplace add .` then `codex plugin add <name>@ooj-tools`.

## Rules

- Work on topic branches in worktrees (`worktrees/<topic>/`); never commit
  directly to `master`.
- A plugin is installable in a runtime only if that runtime's marketplace
  manifest lists it; keep marketplace descriptions in sync with the plugin's
  `plugin.json`.
- `plugins/dox/` maintains its own dox-managed AGENTS.md tree — read
  [`plugins/dox/AGENTS.md`](plugins/dox/AGENTS.md) before editing there.

## References

- Claude Code: [plugin structure](https://code.claude.com/docs/en/plugins-reference) ·
  [marketplace schema](https://code.claude.com/docs/en/plugin-marketplaces)
- Codex: [build plugins & marketplaces](https://developers.openai.com/codex/plugins/build) ·
  [hooks](https://developers.openai.com/codex/hooks)
- Full link list: [README → Plugin-dev references](README.md#plugin-dev-references)

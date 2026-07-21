# plugins/

One plugin per directory. Structure contract for every `plugins/<name>/`:

## Manifests

- `.claude-plugin/plugin.json` — required (Claude Code).
- `.codex-plugin/plugin.json` — optional; Codex falls back to the Claude
  manifest when it is absent.
- Shipping requires a marketplace entry at the repo root:
  `.claude-plugin/marketplace.json` (Claude Code) and/or
  `.agents/plugins/marketplace.json` (Codex).

## Components

- Component directories live at the plugin root, never inside
  `.claude-plugin/`: `commands/*.md`, `agents/*.md`, `skills/<skill>/SKILL.md`,
  `hooks/hooks.json`, `scripts/`.
- Only create the directories the plugin actually uses.

## Gotchas

- Reference intra-plugin paths via `"${CLAUDE_PLUGIN_ROOT}"` (quoted), never
  absolute paths. Codex sets the same variable as a compatibility alias for
  its native `${PLUGIN_ROOT}`.
- `hooks/hooks.json` is auto-discovered by BOTH runtimes. A runtime-specific
  hooks file must live at a non-default path (e.g. `hooks/claude-hooks.json`)
  and be pointed to from that runtime's plugin manifest via its `"hooks"`
  field.
- `plugins/dox/dist/` is committed on purpose (plugin installs don't run npm);
  rebuild and commit it in the same change as any `src/` edit.
- A plugin that wants a dox-managed AGENTS.md tree adds `.dox.json` at its
  root; the git pre-commit gate (`plugins/dox/hooks/git/pre-commit`) checks
  every `plugins/*/` that opts in.

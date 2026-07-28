# ooj-skills

One bundle for every loose skill — small, self-contained skills that don't
warrant a full plugin each. There are no themed splits: a skill lands here
regardless of topic unless it genuinely needs a plugin's machinery. Pure
markdown: no hooks, scripts, or commands. The convention is documented in
[`plugins/AGENTS.md`](../AGENTS.md).

| Skill | Trigger examples | What it does |
|-------|------------------|--------------|
| `conventional-commits` | "write a conventional commit", "format this commit message", "what type should this commit be" | Concise Conventional Commits v1.0.0 reference: types, rules, breaking-change syntax, worked examples, and a staged-diff-first process. |

In Codex, invoke a skill by name: `$conventional-commits`.

## Install

From the ooj-tools marketplace:

```
/plugin install ooj-skills@ooj-tools
```

Or try it in one session without installing:

```
claude --plugin-dir /path/to/ooj-tools/plugins/ooj-skills
```

For Codex:

```bash
codex plugin add ooj-skills@ooj-tools
```

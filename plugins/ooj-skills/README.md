# ooj-skills

One bundle for every loose skill — small, self-contained skills that don't
warrant a full plugin each. There are no themed splits: a skill lands here
regardless of topic unless it genuinely needs a plugin's machinery. Pure
markdown: no hooks, scripts, or commands. The convention is documented in
[`plugins/AGENTS.md`](../AGENTS.md).

| Skill | Trigger examples | What it does |
|-------|------------------|--------------|
| `conventional-commits` | "write a conventional commit", "format this commit message", "what type should this commit be" | Concise Conventional Commits v1.0.0 reference: types, spec requirements kept separate from optional house style, breaking-change syntax, worked examples, and a staged-diff-first process. |
| `asd-ste100` | "write in Simplified Technical English", "convert this to ASD-STE100", "make this doc plain/unambiguous" | ASD-STE100 Simplified Technical English reference: the approved-word dictionary principle, the writing rules that reshape most text, sentence/paragraph limits, and a conversion process — for generated prose or existing text being rewritten. |
| `readme` | "write a README", "generate a README for this repo", "improve/restructure this README", "add badges and sections" | Generate or upgrade a standard GitHub-style README by inspecting the repo: a required/optional section backbone with archetype inserts, shields.io badges, GitHub admonitions, an inspect-then-fill process, and a fill-in template. |

In Codex, invoke a skill by name: `$conventional-commits`, `$asd-ste100`, `$readme`.

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

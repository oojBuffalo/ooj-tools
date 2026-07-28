---
name: conventional-commits
description: This skill should be used when the user asks to "write a conventional commit", "format this commit message", "what type or scope should this commit be", or otherwise wants commit messages that follow the Conventional Commits spec. In Codex, use when the user invokes $conventional-commits.
---

# Conventional Commits

Write commit messages per [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | Use for | SemVer |
|------|---------|--------|
| `feat` | New user-facing capability | MINOR |
| `fix` | Bug fix | PATCH |
| `build` | Build system or external dependencies | — |
| `chore` | Maintenance that touches no src/test behavior | — |
| `ci` | CI configuration and scripts | — |
| `docs` | Documentation only | — |
| `perf` | Performance improvement without behavior change | — |
| `refactor` | Code change that neither fixes nor adds behavior | — |
| `style` | Formatting, whitespace, missing semicolons | — |
| `test` | Adding or correcting tests | — |

## Rules

- Description: imperative mood, lowercase, no trailing period, aim for ≤50
  characters in the subject line.
- Scope is optional, parenthesized, and names the affected module:
  `fix(parser): …`.
- Separate body and footers from the subject with a blank line; wrap body at
  ~72 characters and explain *what* and *why*, not how.
- Breaking changes: append `!` after the type/scope and/or add a
  `BREAKING CHANGE: <explanation>` footer (either alone is sufficient; `!`
  is the more visible choice). Always MAJOR in SemVer.
- Footers use `Token: value` with `-` in place of spaces in multi-word tokens
  (e.g. `Reviewed-by: Alice`, `Refs: #123`); `BREAKING CHANGE` is the one
  token allowed to contain a space.

## Examples

```
fix: prevent racing of requests
```

```
feat(lang): add polish language
```

```
feat(api)!: send an email to the customer when a product is shipped
```

```
refactor(runtime): drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.

Refs: #123
```

## Process

1. Inspect the staged diff (`git diff --staged`) before writing anything.
2. Pick the type from the dominant change; if the diff mixes unrelated types,
   suggest splitting into one commit per logical change.
3. Derive the scope from the touched module or directory; omit it when the
   change is cross-cutting.
4. Follow any stricter project convention (commitlint config, CONTRIBUTING.md)
   over the defaults above when they conflict.

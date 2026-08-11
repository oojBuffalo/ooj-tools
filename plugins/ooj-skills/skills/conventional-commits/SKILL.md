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

`feat` and `fix` are the only types the spec defines; it permits any other
type. The rest of this table is the widely used Angular set — convention, not
spec.

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

## Spec requirements

These are what v1.0.0 actually mandates:

- Prefix: `<type>[(scope)][!]: ` — the terminal colon and space are required,
  and the description follows immediately.
- Scope, when present, is a noun in parentheses naming a section of the
  codebase: `fix(parser): …`.
- The body is optional and free-form; it must begin one blank line after the
  description.
- Footers are optional, begin one blank line after the body, and take the form
  `Token: value` or `Token #value`. Tokens use `-` in place of spaces
  (`Reviewed-by: Alice`); `BREAKING CHANGE` is the one token allowed a space.
- Breaking changes: `!` before the colon and/or a `BREAKING CHANGE: <explanation>`
  footer (either alone is sufficient; `!` is the more visible choice). Always
  MAJOR in SemVer. The footer token must be uppercase; `BREAKING-CHANGE` is an
  accepted synonym.
- Casing is otherwise not significant — the spec treats these units as
  case-insensitive, `BREAKING CHANGE` excepted.

## Style recommendations

Not part of the spec. Apply them only when the project already follows them,
or when the user wants house style on top of spec compliance — never silently
in response to a bare request for a conventional commit:

- Description in imperative mood, lowercase, no trailing period.
- Subject line ≤50 characters; body wrapped at ~72.
- Body explains *what* and *why*, not how.

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
4. Meet the spec requirements always; adopt the style recommendations only
   when the project's own convention (commitlint config, CONTRIBUTING.md, the
   existing `git log`) calls for them, and prefer that convention when it
   conflicts.

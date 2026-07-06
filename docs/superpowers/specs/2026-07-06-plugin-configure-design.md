# plugin-configure — design spec

- **Date:** 2026-07-06
- **Status:** awaiting user sign-off
- **Branch:** `feat/plugin-configure` (worktree `.claude/worktrees/plugin-configure/`)

## Problem

Every brand-new repo/dir starts with all 42 personal skills and every user-scope
plugin ON. Native `/skills` and `/plugin` choices are repo-sticky but don't travel to
fresh dirs, so each new repo forces a full manual re-curation (~27 skill toggles plus
plugin disables). That cold-start reset is the entire problem.

## Solution overview

`plugin-configure` is a plugin in the ooj-tools marketplace. On the first session in an
unconfigured git repo, its SessionStart hook nudges the model to offer a one-card
profile pick (native `AskUserQuestion`). Picking a profile stamps repo-local settings —
`skillOverrides` and plugin enable/disable arrays in `.claude/settings.local.json` —
plus a marker file. All granular follow-up editing stays in the native `/skills` and
`/plugin` menus; this plugin only solves the cold start.

## Decisions (user-confirmed; summary)

| Topic | Decision |
|---|---|
| Scope | Profiles-first cold-start stamp; no custom granular TUI (ADR-001/002, prior session) |
| Skill discovery | Scan `~/.claude/skills/` + project `.claude/skills/`. Bundled skills (embedded in the CLI binary, unscannable) always stay ON. |
| Semantics | Profiles are **allowlists** — skills/plugins to keep ON; everything else discovered gets turned off. |
| Profile storage | `~/.claude/plugin-configure/profiles.json`, bootstrapped on first run. |
| Write target | `.claude/settings.local.json` (same file native `/skills` writes). |
| Plugins | Stamp manages plugins per-repo via local-scope arrays. |
| Hook | Plugin-shipped SessionStart hook; git repos only; self-preservation of plugin-configure. |
| Idempotency | Dedicated marker `.claude/plugin-configure.json`, added to `.git/info/exclude`. |
| Starter profiles | `general-dev`, `minimal`, `web-dev`, `data-ml`. |

## Components

Plugin lives at `plugins/plugin-configure/` with an entry in
`.claude-plugin/marketplace.json`.

### 1. `.claude-plugin/plugin.json`

`{ "name": "plugin-configure", "version": "0.1.0", "description": ... }`

### 2. SessionStart hook — `hooks/hooks.json` + `hooks/session-start.sh`

Fast (stat/grep checks only), always exits 0, never blocks a session. Emits nothing
unless ALL of:

1. cwd is inside a git repo (`git rev-parse --show-toplevel` succeeds);
2. no marker `<repo-root>/.claude/plugin-configure.json`;
3. `<repo-root>/.claude/settings.local.json` has no `skillOverrides` key
   (grandfathers already-hand-curated repos like ooj-tools).

When all hold, it prints hook JSON:

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart",
  "additionalContext": "This repo has no plugin-configure profile stamped. Offer the user a profile pick by following the /plugin-configure:configure command instructions at ${CLAUDE_PLUGIN_ROOT}/commands/configure.md."}}
```

### 3. Command — `commands/configure.md` (`/plugin-configure:configure`)

Single source of the stamping flow, used by both the hook nudge and manual invocation
(manual works anywhere, including non-git dirs, and a re-run re-stamps over a previous
stamp or skip). Flow:

1. Run `scripts/stamp.py --bootstrap-only` to ensure `profiles.json` exists.
2. Read profile names/descriptions from `profiles.json`.
3. `AskUserQuestion`: profiles from the file as options, up to 4 per card
   ("Other"/dismissal ⇒ skip).
4. Run `scripts/stamp.py <profile>` (or `--skip`).
5. Confirm what was written; note settings apply from the **next** session.

### 4. Engine — `scripts/stamp.py` (python3, stdlib only, Google-style docstrings)

`stamp.py <profile> | --skip | --bootstrap-only` — deterministic, idempotent.

- **Inventory:** skill names = directory entries (dirs/symlinks only, dotfiles
  ignored) of `~/.claude/skills/` plus `<repo-root>/.claude/skills/` if present.
  Plugin state = `claude plugin list --json` (ids + `enabled` + `scope`).
- **Target root:** the git repo root when inside a repo, else cwd (manual command in
  non-git dirs); the `.git/info/exclude` step is skipped outside git repos.
- **Compute:**
  - `skillOverrides` = `{skill: "off"}` for every discovered skill not in
    `profile.skills`.
  - `disabledPlugins` = every plugin currently enabled (any scope) whose id is not in
    `profile.plugins` — always excluding `plugin-configure@ooj-tools` itself.
  - `enabledPlugins` = every id in `profile.plugins` that is installed but currently
    disabled (see "Local enables" below).
- **Write:** deep-merge into `<repo-root>/.claude/settings.local.json` — the stamp owns
  and replaces exactly the keys `skillOverrides`, `disabledPlugins`, `enabledPlugins`;
  all other keys (permissions, hooks, …) are preserved. Atomic tmp+rename write.
- **Marker:** write `.claude/plugin-configure.json`:
  `{"profile": "web-dev", "stampedAt": "<ISO8601>", "pluginVersion": "0.1.0"}` or
  `{"skipped": true, "stampedAt": "<ISO8601>"}`. If in a git repo, append
  `.claude/plugin-configure.json` to `.git/info/exclude` when not already present.
- **`--skip`:** writes only the marker.
- **Bootstrap:** if `~/.claude/plugin-configure/profiles.json` is missing, write the
  starter file (contents below) and report that it did so.
- **Errors:** unknown profile → exit non-zero with the available names; `claude` CLI
  missing/failing → stamp skills only and warn that plugins were left untouched;
  never delete or truncate an existing settings file on failure.

#### Local enables (flagged extension — confirm at review)

The locked decision was disable-only. However, the approved web-dev profile includes
the vercel plugin, which is currently **disabled at user scope** — the only way a
profile can deliver it per-repo is a local-scope enable (local overrides user in
settings precedence). The stamp therefore also writes `enabledPlugins` for profile
plugins that are installed but disabled. Plugins deliberately absent from a profile are
unaffected by this rule.

## Profile schema — `~/.claude/plugin-configure/profiles.json`

```json
{
  "version": 1,
  "profiles": {
    "<name>": {
      "description": "shown in the picker",
      "skills": ["<personal-or-project skill name>", "..."],
      "plugins": ["<name>@<marketplace>", "..."]
    }
  }
}
```

Skills absent from every list are exactly what gets stamped `off`; the file is meant to
be hand-edited freely — the stamp re-reads it every run.

## Starter profile contents

Derived from the live inventory (42 personal skills; 19 user-enabled plugins) and the
hand-curated ooj-tools keep-set. `plugin-configure@ooj-tools` is implicitly always kept.

### minimal — "near-silent scratch work"

- skills: `[]` (all 42 personal skills off)
- plugins: `superpowers@claude-plugins-official`, `remember@claude-plugins-official`

### general-dev — "everyday default" (mirrors your ooj-tools keep-set)

- skills (15): agent-browser, agent-md-refactor, caveman, diagnose, find-skills,
  grill-with-docs, improve-codebase-architecture, prototype, setup-matt-pocock-skills,
  tdd, tmux, to-issues, to-prd, triage, zoom-out
- plugins (12): superpowers, remember, code-review, code-simplifier, github, context7,
  claude-md-management, hookify, pr-review-toolkit, feature-dev, security-guidance
  (all `@claude-plugins-official`) + codex@openai-codex

### web-dev — general-dev plus the frontend stack

- skills: general-dev + react-dev, react-useeffect, vercel-composition-patterns,
  vercel-react-best-practices, vercel-react-native-skills, frontend-design,
  web-design-guidelines, webapp-testing
- plugins: general-dev + playwright@claude-plugins-official +
  vercel@claude-plugins-official *(currently user-disabled → local enable)*

### data-ml — general-dev plus ML tooling

- skills: general-dev + video-frames
- plugins: general-dev + huggingface-skills@claude-plugins-official

### Left out of every starter profile (locally disabled after any stamp)

- skills (18 beyond the profile-specific ones): backend-to-frontend-handoff-docs,
  browser-use, c4-architecture, curses, design-md, frontend-to-backend-requirements,
  grill-me, just-scrape, mermaid-diagrams, opentui, reducing-entropy,
  remotion-best-practices, ship-learn-next, soultrace, ui-ux-pro-max, web-artifacts-builder,
  web-to-markdown, write-a-skill (+ per-profile leftovers)
- plugins: andrej-karpathy-skills@karpathy-skills, atomic-agents, mcp-server-dev,
  resend, skill-creator (+ huggingface-skills/playwright outside their profiles)

These lists are drafts — edit `profiles.json` (or this spec) freely; nothing else in
the design depends on their exact contents.

## Flows

**Cold start:** new repo → hook fires (3 checks pass) → additionalContext → model runs
the configure flow → card pick → `stamp.py general-dev` → settings.local.json +
marker written → "stamped; takes effect next session." Next launch: marker exists →
hook silent; `/skills` shows the offs.

**Skip:** card dismissed or "Other: skip" → `stamp.py --skip` → marker only → never
nagged again in that repo; everything stays on.

**Re-stamp / switch profile:** user runs `/plugin-configure:configure` anywhere →
same flow; stamp replaces the three owned keys and the marker.

**Hand-curated repo (e.g. ooj-tools):** `skillOverrides` already present → hook silent
forever; nothing written.

## Out of scope

- Bundled skills (always on; unscannable and never part of the pain).
- Granular per-skill UI (native `/skills`), plugin browsing (`/plugin`).
- Retro-syncing existing repos, profile "sync" after skill installs (re-stamp covers it).
- Multi-machine sync of profiles.json.

## Testing

1. **Engine tests** (stdlib `unittest`, no dev dependencies):
   fixture temp git repo → run stamp.py with a fixture profiles.json and a stubbed
   `claude plugin list --json` → assert: computed off-map matches inventory minus
   allowlist; existing settings keys preserved; atomic replace; marker contents;
   `.git/info/exclude` line added once; `--skip` touches only the marker;
   self-preservation of plugin-configure; unknown profile errors cleanly.
2. **Hook tests:** run session-start.sh in (a) non-git dir, (b) git repo w/o marker,
   (c) with marker, (d) with skillOverrides present — assert silence/JSON exactly.
3. **E2E:** `claude --plugin-dir` (per dox testing instructions) in a scratch repo →
   nudge → pick → verify files; relaunch → no nudge, `/skills` reflects offs;
   ooj-tools → no nudge; non-git dir → no nudge; `/plugin-configure:configure` re-stamp
   switches profiles.

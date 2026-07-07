# plugin-configure

Cold-start skill/plugin curation for Claude Code. Every brand-new repo starts
with all personal skills and user-scope plugins ON; native `/skills` and
`/plugin` choices are repo-sticky but don't travel to fresh dirs. This plugin
writes a curated **profile** into a repo's `.claude/settings.local.json` on
first launch, then gets out of the way — granular follow-ups stay in the
native `/skills` and `/plugin` menus.

## How it works

- A SessionStart hook fires in every session. In an unconfigured git repo (no
  marker, no existing `skillOverrides`) it asks the model to offer a one-card
  profile pick; everywhere else it is silent.
- Picking a profile runs `scripts/apply_profile.py`, which:
  - scans `~/.claude/skills/` + `<repo>/.claude/skills/` and writes
    `skillOverrides: {<non-profile skill>: "off"}`;
  - reads `claude plugin list --json` and writes local `disabledPlugins`
    (enabled plugins not in the profile) and `enabledPlugins` (profile plugins
    currently disabled). It never disables itself;
  - writes the marker `.claude/plugin-configure.json` (profile, timestamp) and
    adds it to `.git/info/exclude`.
- Skipping writes only the marker (`{"skipped": true}`) so the nudge never
  repeats in that repo.
- Bundled skills are untouched (they are not on disk and are curated by
  Anthropic); repos that already have `skillOverrides` are never nagged.

## Profiles

Allowlists (what stays ON) live in `~/.claude/plugin-configure/profiles.json`,
bootstrapped on first run with `general-dev`, `minimal`, `web-dev` and
`data-ml`. Edit freely — the file is re-read on every run.

## Usage

- Automatic: open Claude Code in a fresh git repo and answer the card.
- Manual / re-apply / non-git dirs: `/plugin-configure:configure`
- Headless skip: `python3 scripts/apply_profile.py --skip`

## Tests

```
python3 plugins/plugin-configure/tests/test_apply_profile.py -v
bash plugins/plugin-configure/tests/test_hook.sh
```

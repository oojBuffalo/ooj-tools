# plugin-configure — session handoff

> **Read this first.** A prior session designed this plugin but ran out of context.
> This file is **self-contained** — it inlines every hard-won fact so you can resume
> cold without the old transcript. We are in **design/grilling**, NOT implementation.
> **Do not write plugin code yet** (see "Gate" below).
>
> **Where you are:** this file lives in the worktree
> `/Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/` on branch
> **`feat/plugin-configure`** (off `master`). The plugin build happens on this same
> branch. From the ooj-tools root you can read it at
> `.claude/worktrees/plugin-configure/PLUGIN-CONFIGURE-HANDOFF.md`.

---

## 0. One-paragraph orientation

We're designing a new plugin called **`plugin-configure`** for the user's personal
Claude Code marketplace **ooj-tools** (`/Users/ooj/Fun/code/ooj-tools`). It solves one
specific annoyance: **every brand-new repo/dir starts with all 50+ skills/plugins ON**,
forcing the user to manually re-curate every time. Native `/skills` already makes
per-skill choices *repo-sticky within a dir* — but those choices **don't travel to a
fresh dir**, so each new repo resets to "everything on." That **cold-start reset** is
the entire problem we're solving.

---

## 1. Locked decisions (do not relitigate)

- **ADR-001 — Scope = A (profiles-first). ACCEPTED, user-confirmed.**
  On first launch in an unconfigured repo, prompt (native `AskUserQuestion`) to **stamp
  a curated profile** into the repo's settings. Granular edits afterward are handled by
  the **native `/skills` and `/plugin` menus** — we do NOT build our own granular TUI.
  - Rejected **Option C (custom granular TUI)**: `/skills` already gives native,
    repo-sticky, per-skill control — a TUI would duplicate it (YAGNI).
  - Rejected **Option B**.
- **ADR-002 — Tool's job = cold-start profile stamp. ACCEPTED.**
  Stamp once on first launch in an unconfigured repo; native menus handle the rest.

---

## 2. Verified platform facts (hard-won — trust these, they're checked)

- **`/skills` is a native menu and IS repo-sticky.** Writes `skillOverrides` to
  `.claude/settings.local.json` (project-local, gitignored). Space cycles state, Enter
  saves. Source: https://code.claude.com/docs/en/skills (line 572).
  **User confirmed empirically:** sticks in the *same* dir; **resets in a new dir**
  (scope is per-directory, doesn't travel). That reset is the cold-start pain.
- **`skillOverrides` states:** `on` | `name-only` | `user-invocable-only` | `off`.
  Absent key ⇒ `on`. **There is NO wildcard** — to turn skills off by default you must
  **enumerate every skill** and set each to `off`. (This drives open branch #2.)
- **`skillOverrides` covers** bundled + personal (`~/.claude/skills/`) + project skills.
  It does **NOT** cover *plugin* skills — those are governed by `/plugin`; they're
  namespaced `plugin:skill`.
- **Plugins:** `/plugin` and `claude plugin enable/disable` default to **USER scope**
  (global, NOT repo-sticky). `--scope project|local` makes them repo-sticky. Uses arrays
  `enabledPlugins` / `disabledPlugins`. Id format `name@marketplace`. A plugin not listed
  anywhere is fully inert.
- **Personal skills dir doubles as a plugin source:** `~/.claude/skills/<name>/` with a
  `.claude-plugin/plugin.json` loads as `<name>@skills-dir`.
- **Hooks are output-only** — they CANNOT render menus or block. A `SessionStart` hook
  fires on startup (including in unconfigured dirs; a **user-level** hook always runs
  regardless of project config). It can inject context via stdout JSON:
  `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`.
  → So the trigger is: hook detects "unconfigured" → injects a nudge → the model calls
  `AskUserQuestion` → writes the settings files. The hook itself can't draw the menu.
- **`AskUserQuestion` (native card UI):** max **4 options/card, 4 cards** (~16 items).
  Perfect for a profile pick; CANNOT render a 50-item checklist. (Reinforces profiles > TUI.)
- **Plugin bundle layout:** `.claude-plugin/plugin.json` (only `name` required); optional
  `commands/`, `skills/<name>/SKILL.md`, `agents/`, `hooks/hooks.json`, `.mcp.json`
  (or inline `mcpServers`). Path var `${CLAUDE_PLUGIN_ROOT}`.
- **Local marketplace:** `.claude-plugin/marketplace.json` =
  `{name, owner, plugins:[{name, source:"./plugins/<name>"}]}`. ooj-tools already is one.
- **Settings precedence (high→low):** managed → CLI → local
  (`.claude/settings.local.json`) → project (`.claude/settings.json`) → user
  (`~/.claude/settings.json`).
- **Lean launch flags (session-only, for reference):** `--safe-mode`, `--bare`
  (sets `CLAUDE_CODE_SIMPLE=1`), `--setting-sources user,project,local`,
  `--strict-mcp-config` + `--mcp-config`, `--disable-slash-commands`.
- **User env:** Claude Code **v2.1.201**.

---

## 3. Repo facts (ooj-tools)

- Path: `/Users/ooj/Fun/code/ooj-tools`. Primary branch is **`master`** (protected by a
  `block-main-edits.sh` hook — writes to master are blocked; work on a worktree branch).
- It's already a marketplace: `.claude-plugin/marketplace.json` (name `ooj-tools`, owner
  Elijah Wilt). One existing plugin: **`dox`** — **user said explicitly: IGNORE dox as a
  reference for this plugin. It's unrelated.**
- ooj-tools has an untracked `.claude/` dir with a hand-maintained `skillOverrides`
  (~24 `off` entries) in `.claude/settings.local.json` — proof the mechanism works.
- New plugin will live at `plugins/plugin-configure/` + an entry in `marketplace.json`.
- **Active branch for this work:** `feat/plugin-configure` (worktree at
  `.claude/worktrees/plugin-configure/`). Build here, not on master.

---

## 4. Open branches — RESUME HERE (dependency order)

Continue the `grill-me` / `superpowers:brainstorming` flow. Ask ONE question at a time,
give your recommended answer with each. **Start with #2 — it's the feasibility risk.**

1. **Profile definition & storage** — how many profiles, what each contains, where they
   live (a user-level file like `~/.claude/…/profiles.json`, or inside the plugin?),
   schema. Allowlist (off-by-default + explicit on) vs denylist per profile.
2. **Skill discovery (KEY FEASIBILITY RISK)** — no wildcard ⇒ the stamp must enumerate
   ALL installed skills to set them `off` (minus the allowlist). How does the plugin
   discover the full skill list at stamp time — is there a CLI/programmatic source, or do
   we scan `~/.claude/skills/` + project `.claude/skills/` + the bundled set? Resolve early.
3. **Write target** — `settings.local.json` (personal, gitignored, matches `/skills`) vs
   `settings.json` (shared/committed). Likely local for `skillOverrides`; TBD for
   `enabledPlugins`.
4. **Plugin handling** — does a profile also set `enabledPlugins`, and at which scope?
   Open Q for the user: do plugin sets vary per-repo, or are they basically on-everywhere?
5. **Trigger UX** — SessionStart hook detects "unconfigured" (define exactly: no
   `skillOverrides` key? no `.claude/settings.local.json`? a marker file?) → injects
   `additionalContext` → model runs `AskUserQuestion` profile pick → writes files. Needs
   an **idempotency marker** so it stops nagging even after "skip." Hook lives at USER
   level (the only layer guaranteed to run in an unconfigured repo).
6. **Actual profile contents** — derive real profiles (e.g. minimal / web-dev / data /
   full?) from the user's real skill+plugin inventory.

After branches resolve → write the spec to
`docs/superpowers/specs/YYYY-MM-DD-plugin-configure-design.md`, do the spec self-review,
get user sign-off, then invoke **`superpowers:writing-plans`** (the ONLY skill after
brainstorming).

---

## 5. Gate & constraints (MUST honor)

- **HARD GATE (brainstorming skill):** do NOT write plugin code, scaffold, or invoke any
  implementation skill until a design is presented AND the user approves it.
- **Never work on the primary branch.** All build work happens on the
  `feat/plugin-configure` worktree branch (already created), never on `master`. A
  `block-main-edits.sh` hook enforces this.
- **No AI attribution** in any commit message or PR body (no `Co-Authored-By: Claude`, no
  `Generated with…`, no `claude.ai/code` link). End commits on the last real content line.
- **Do NOT begin implementation tasks unless explicitly told.**

---

## 6. Harness gotcha (so you don't get confused)

The Claude Code **session cwd is fixed at launch and can't be changed from a tool call.**
The prior session launched in `career-ops`, so the shell kept resetting cwd to
`/Users/ooj/Fun/code/career-ops` even after `cd`. All ooj-tools work was done via
**absolute paths**. For a clean next session, the user should relaunch with
`cd /Users/ooj/Fun/code/ooj-tools && claude` (or `/add-dir` it).

---

## 7. Exact next action

Resume the grilling. Open with **Branch #2 (skill discovery)**: investigate how to
enumerate every installed skill (probe `~/.claude/skills/`, project `.claude/skills/`,
bundled skills, and any `claude` CLI that lists skills), present your recommended
discovery mechanism, and get the user's call. Then walk the remaining branches in order.

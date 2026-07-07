# plugin-configure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A plugin that, on first launch in an unconfigured git repo, writes a curated skill/plugin profile into `.claude/settings.local.json` so new repos don't start with all 42 personal skills and 19 plugins on.

**Architecture:** Three parts: a deterministic python3 engine (`scripts/apply_profile.py`) that discovers installed skills/plugins and merge-writes the repo-local settings + a marker file; a SessionStart hook that nudges the model only in unconfigured git repos; and a slash command (`/plugin-configure:configure`) holding the single interactive flow (profile pick via AskUserQuestion → run engine). Profiles are user-level allowlists in `~/.claude/plugin-configure/profiles.json`, bootstrapped on first run.

**Tech Stack:** python3 (stdlib only), bash, Claude Code plugin bundle (hooks.json / commands / `${CLAUDE_PLUGIN_ROOT}`).

**Spec:** `docs/superpowers/specs/2026-07-06-plugin-configure-design.md` (approved 2026-07-06).

## Global Constraints

- Work ONLY on branch `feat/plugin-configure` in the worktree `/Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/` (repo root for all paths below). Never touch `master`.
- No AI attribution anywhere in commit messages (no `Co-Authored-By: Claude`, no `Generated with`, no session links). End commits on the last real content line.
- `scripts/apply_profile.py`: python3 **stdlib only**, Google-style docstrings (Args/Returns/Raises).
- The hook must ALWAYS exit 0 and stay silent on every non-nudge path — it must never block or slow a session.
- The script owns exactly three settings keys: `skillOverrides`, `disabledPlugins`, `enabledPlugins`. Every other key in `.claude/settings.local.json` must survive a profile application byte-for-byte in value.
- The script never disables `plugin-configure@ooj-tools` (self-preservation).
- Bundled skills are never written to `skillOverrides` (only names discovered by directory scan).
- Marker file is `.claude/plugin-configure.json` relative to the target root; it must be added to `.git/info/exclude` (never to a committed `.gitignore`).
- Run all commands from the worktree root: `/Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure`.

---

### Task 1: Plugin scaffold + marketplace entry

**Files:**
- Create: `plugins/plugin-configure/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md:15` (plugins table)

**Interfaces:**
- Consumes: nothing.
- Produces: the plugin directory `plugins/plugin-configure/` and the id `plugin-configure@ooj-tools` that all later tasks build inside; marketplace + README entries.

- [ ] **Step 1: Create the plugin manifest**

Create `plugins/plugin-configure/.claude-plugin/plugin.json`:

```json
{
  "name": "plugin-configure",
  "version": "0.1.0",
  "description": "Cold-start skill/plugin curation: on first launch in an unconfigured repo, writes a chosen profile (skillOverrides + plugin enables/disables) into .claude/settings.local.json, so new repos don't start with everything on.",
  "author": {
    "name": "Elijah Wilt",
    "email": "elijahwilt.github@gmail.com"
  },
  "license": "MIT",
  "homepage": "https://github.com/oojBuffalo/ooj-tools/tree/master/plugins/plugin-configure",
  "repository": "https://github.com/oojBuffalo/ooj-tools",
  "keywords": ["skills", "plugins", "profiles", "settings", "cold-start"]
}
```

(No per-plugin LICENSE file: root README says plugins only carry one if it differs from the collection's MIT.)

- [ ] **Step 2: Add the marketplace entry**

In `.claude-plugin/marketplace.json`, append to the `plugins` array (after the `dox` entry):

```json
    {
      "name": "plugin-configure",
      "source": "./plugins/plugin-configure",
      "description": "Cold-start profile setup: offers a curated skill/plugin profile on first launch in an unconfigured repo and writes it to .claude/settings.local.json; native /skills and /plugin menus handle everything after."
    }
```

- [ ] **Step 3: Add the README table row**

In `README.md`, add below the `dox` row of the Plugins table:

```markdown
| [`plugin-configure`](plugins/plugin-configure/) | Cold-start profile setup: offers a curated skill/plugin profile on first launch in an unconfigured repo and writes it to `.claude/settings.local.json`. |
```

- [ ] **Step 4: Validate**

Run: `claude plugin validate plugins/plugin-configure && claude plugin validate .`
Expected: both report valid (exit 0). If the marketplace validation complains about the new entry, fix the JSON until clean.

- [ ] **Step 5: Commit**

```bash
git add plugins/plugin-configure/.claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "scaffold plugin-configure plugin and marketplace entry"
```

---

### Task 2: apply_profile.py pure computation core (TDD)

**Files:**
- Create: `plugins/plugin-configure/scripts/apply_profile.py`
- Test: `plugins/plugin-configure/tests/test_apply_profile.py`

**Interfaces:**
- Consumes: nothing.
- Produces (exact signatures later tasks call):
  - `SELF_PLUGIN_ID = "plugin-configure@ooj-tools"` (str constant)
  - `effective_plugin_state(records) -> dict` — `records` is the parsed list from `claude plugin list --json` (dicts with `id`, `enabled`, `scope`); returns `{plugin_id: bool}` using local > project > user precedence.
  - `compute_skill_overrides(discovered, allowed) -> dict` — `discovered` is a set of skill names, `allowed` a list; returns `{name: "off"}` for every discovered name not allowed, keys sorted.
  - `compute_plugin_arrays(state, allowed) -> (list, list)` — returns `(disabled, enabled)`: enabled-but-unlisted ids to disable (never `SELF_PLUGIN_ID`), and listed-but-currently-disabled installed ids to enable. Both sorted.
  - `merge_settings(existing, overrides, disabled, enabled, plugins_known) -> dict` — non-destructive merge owning only the three owned settings keys; when `plugins_known` is False the two plugin arrays are left exactly as in `existing`.

- [ ] **Step 1: Write the failing tests**

Create `plugins/plugin-configure/tests/test_apply_profile.py`:

```python
#!/usr/bin/env python3
"""Tests for scripts/apply_profile.py. Run: python3 plugins/plugin-configure/tests/test_apply_profile.py -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_profile


class EffectivePluginStateTests(unittest.TestCase):
    def test_single_user_record(self):
        records = [{"id": "a@m", "enabled": True, "scope": "user"}]
        self.assertEqual(apply_profile.effective_plugin_state(records), {"a@m": True})

    def test_local_beats_user(self):
        records = [
            {"id": "a@m", "enabled": True, "scope": "user"},
            {"id": "a@m", "enabled": False, "scope": "local"},
        ]
        self.assertEqual(apply_profile.effective_plugin_state(records), {"a@m": False})

    def test_project_beats_user_regardless_of_order(self):
        records = [
            {"id": "a@m", "enabled": True, "scope": "project"},
            {"id": "a@m", "enabled": False, "scope": "user"},
        ]
        self.assertEqual(apply_profile.effective_plugin_state(records), {"a@m": True})

    def test_record_without_id_is_ignored(self):
        records = [{"enabled": True, "scope": "user"}]
        self.assertEqual(apply_profile.effective_plugin_state(records), {})


class ComputeSkillOverridesTests(unittest.TestCase):
    def test_non_allowed_skills_turn_off_sorted(self):
        result = apply_profile.compute_skill_overrides({"zeta", "alpha", "tdd"}, ["tdd"])
        self.assertEqual(result, {"alpha": "off", "zeta": "off"})
        self.assertEqual(list(result), ["alpha", "zeta"])

    def test_empty_allowlist_turns_everything_off(self):
        result = apply_profile.compute_skill_overrides({"a", "b"}, [])
        self.assertEqual(result, {"a": "off", "b": "off"})

    def test_allowed_name_not_discovered_is_ignored(self):
        result = apply_profile.compute_skill_overrides({"a"}, ["ghost"])
        self.assertEqual(result, {"a": "off"})


class ComputePluginArraysTests(unittest.TestCase):
    def test_enabled_unlisted_gets_disabled(self):
        state = {"a@m": True, "b@m": True}
        disabled, enabled = apply_profile.compute_plugin_arrays(state, ["a@m"])
        self.assertEqual(disabled, ["b@m"])
        self.assertEqual(enabled, [])

    def test_self_is_never_disabled(self):
        state = {apply_profile.SELF_PLUGIN_ID: True, "b@m": True}
        disabled, _ = apply_profile.compute_plugin_arrays(state, [])
        self.assertEqual(disabled, ["b@m"])

    def test_listed_but_disabled_gets_enabled(self):
        state = {"a@m": False}
        disabled, enabled = apply_profile.compute_plugin_arrays(state, ["a@m"])
        self.assertEqual(disabled, [])
        self.assertEqual(enabled, ["a@m"])

    def test_listed_but_not_installed_is_ignored(self):
        disabled, enabled = apply_profile.compute_plugin_arrays({}, ["ghost@m"])
        self.assertEqual(disabled, [])
        self.assertEqual(enabled, [])


class MergeSettingsTests(unittest.TestCase):
    def test_foreign_keys_survive(self):
        existing = {"permissions": {"allow": ["Bash(ls *)"]}}
        merged = apply_profile.merge_settings(existing, {"a": "off"}, ["p@m"], [], True)
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls *)"]})
        self.assertEqual(merged["skillOverrides"], {"a": "off"})
        self.assertEqual(merged["disabledPlugins"], ["p@m"])

    def test_old_overrides_replaced_wholesale(self):
        existing = {"skillOverrides": {"stale": "off"}}
        merged = apply_profile.merge_settings(existing, {"fresh": "off"}, [], [], True)
        self.assertEqual(merged["skillOverrides"], {"fresh": "off"})

    def test_empty_arrays_remove_stale_keys(self):
        existing = {"disabledPlugins": ["old@m"], "enabledPlugins": ["old2@m"]}
        merged = apply_profile.merge_settings(existing, {}, [], [], True)
        self.assertNotIn("disabledPlugins", merged)
        self.assertNotIn("enabledPlugins", merged)

    def test_plugins_unknown_leaves_arrays_untouched(self):
        existing = {"disabledPlugins": ["keep@m"]}
        merged = apply_profile.merge_settings(existing, {}, [], [], False)
        self.assertEqual(merged["disabledPlugins"], ["keep@m"])

    def test_existing_dict_not_mutated(self):
        existing = {"skillOverrides": {"stale": "off"}}
        apply_profile.merge_settings(existing, {"fresh": "off"}, [], [], True)
        self.assertEqual(existing["skillOverrides"], {"stale": "off"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apply_profile'`.

- [ ] **Step 3: Implement the computation core**

Create `plugins/plugin-configure/scripts/apply_profile.py`:

```python
#!/usr/bin/env python3
"""Apply a curated skill/plugin profile to a repo's local Claude Code settings.

Usage:
    apply_profile.py <profile>          Apply the named profile to the current repo/dir.
    apply_profile.py --skip             Record a skip marker only (silences the nudge).
    apply_profile.py --bootstrap-only   Ensure profiles.json exists, list profiles, exit.

Profiles are allowlists (skills/plugins to keep ON) read from
~/.claude/plugin-configure/profiles.json, bootstrapped with starter profiles on
first run. Applying a profile writes .claude/settings.local.json (owning only the
skillOverrides / disabledPlugins / enabledPlugins keys), a marker at
.claude/plugin-configure.json, and a .git/info/exclude entry for the marker.
"""

import json

SELF_PLUGIN_ID = "plugin-configure@ooj-tools"

_SCOPE_RANK = {"user": 1, "project": 2, "local": 3}


def effective_plugin_state(records):
    """Collapse `claude plugin list --json` records into effective enabled state.

    A plugin can have one record per scope; the effective state is the record
    with the highest-precedence scope (local > project > user).

    Args:
        records: List of dicts with at least "id", "enabled" and "scope" keys.

    Returns:
        Dict mapping plugin id to its effective enabled bool.
    """
    best = {}
    for rec in records:
        pid = rec.get("id")
        if not pid:
            continue
        rank = _SCOPE_RANK.get(rec.get("scope"), 0)
        if pid not in best or rank > best[pid][0]:
            best[pid] = (rank, bool(rec.get("enabled")))
    return {pid: enabled for pid, (_, enabled) in best.items()}


def compute_skill_overrides(discovered, allowed):
    """Build the skillOverrides map for a profile.

    Args:
        discovered: Set of skill names found by directory scan.
        allowed: Skill names the profile keeps on.

    Returns:
        Dict of {skill_name: "off"} for every discovered skill not in
        `allowed`, insertion-ordered by sorted name.
    """
    allowed_set = set(allowed)
    return {name: "off" for name in sorted(discovered) if name not in allowed_set}


def compute_plugin_arrays(state, allowed):
    """Compute the local-scope plugin arrays for a profile.

    Args:
        state: Effective plugin state from effective_plugin_state().
        allowed: Plugin ids ("name@marketplace") the profile keeps enabled.

    Returns:
        Tuple (disabled, enabled), both sorted: currently-enabled ids to
        disable (never SELF_PLUGIN_ID), and profile ids that are installed but
        currently disabled, to enable locally.
    """
    allowed_set = set(allowed) | {SELF_PLUGIN_ID}
    disabled = sorted(pid for pid, on in state.items() if on and pid not in allowed_set)
    enabled = sorted(pid for pid in set(allowed) if pid in state and not state[pid])
    return disabled, enabled


def merge_settings(existing, overrides, disabled, enabled, plugins_known):
    """Merge profile-owned keys into a settings dict, preserving everything else.

    The script owns exactly skillOverrides, disabledPlugins and enabledPlugins.
    Empty arrays remove their key (stale state from a previous run). When
    plugins_known is False the two plugin arrays are left exactly as they were,
    because the plugin inventory could not be read.

    Args:
        existing: Parsed current settings (may be empty).
        overrides: skillOverrides map to install.
        disabled: disabledPlugins list to install.
        enabled: enabledPlugins list to install.
        plugins_known: Whether the plugin inventory was available.

    Returns:
        A new merged settings dict; `existing` is not mutated.
    """
    merged = dict(existing)
    merged["skillOverrides"] = dict(overrides)
    if plugins_known:
        for key, value in (("disabledPlugins", list(disabled)),
                           ("enabledPlugins", list(enabled))):
            if value:
                merged[key] = value
            else:
                merged.pop(key, None)
    return merged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: all tests PASS (OK).

- [ ] **Step 5: Commit**

```bash
git add plugins/plugin-configure/scripts/apply_profile.py plugins/plugin-configure/tests/test_apply_profile.py
git commit -m "add apply_profile.py computation core with tests"
```

---

### Task 3: Starter profiles + bootstrap (TDD)

**Files:**
- Modify: `plugins/plugin-configure/scripts/apply_profile.py`
- Test: `plugins/plugin-configure/tests/test_apply_profile.py`

**Interfaces:**
- Consumes: `atomic-write` helper is introduced here and reused by Task 4.
- Produces:
  - `STARTER_PROFILES` (dict): `{"version": 1, "profiles": {"general-dev"|"minimal"|"web-dev"|"data-ml": {"description", "skills", "plugins"}}}`
  - `atomic_write_json(path, data) -> None` — tmp file + `os.replace`, indent=2, trailing newline.
  - `ensure_profiles(path) -> (dict, bool)` — loads profiles.json, writing `STARTER_PROFILES` first when missing; returns `(profiles_doc, created)`.
  - `PROFILES_PATH` (Path constant): `Path.home() / ".claude" / "plugin-configure" / "profiles.json"`.

- [ ] **Step 1: Add the failing tests**

Append to `plugins/plugin-configure/tests/test_apply_profile.py` (before the `if __name__` block; also add `import json`, `import tempfile` and `import os` to the imports at the top):

```python
class StarterProfilesTests(unittest.TestCase):
    def test_four_profiles_exist(self):
        self.assertEqual(
            sorted(apply_profile.STARTER_PROFILES["profiles"]),
            ["data-ml", "general-dev", "minimal", "web-dev"],
        )

    def test_general_dev_keep_set(self):
        profile = apply_profile.STARTER_PROFILES["profiles"]["general-dev"]
        self.assertEqual(len(profile["skills"]), 15)
        self.assertIn("tdd", profile["skills"])
        self.assertEqual(len(profile["plugins"]), 12)
        self.assertIn("superpowers@claude-plugins-official", profile["plugins"])

    def test_minimal_is_near_silent(self):
        profile = apply_profile.STARTER_PROFILES["profiles"]["minimal"]
        self.assertEqual(profile["skills"], [])
        self.assertEqual(
            profile["plugins"],
            ["remember@claude-plugins-official", "superpowers@claude-plugins-official"],
        )

    def test_web_dev_is_general_superset(self):
        profiles = apply_profile.STARTER_PROFILES["profiles"]
        self.assertTrue(set(profiles["general-dev"]["skills"]) < set(profiles["web-dev"]["skills"]))
        self.assertIn("vercel@claude-plugins-official", profiles["web-dev"]["plugins"])

    def test_data_ml_adds_huggingface(self):
        profiles = apply_profile.STARTER_PROFILES["profiles"]
        self.assertIn("huggingface-skills@claude-plugins-official", profiles["data-ml"]["plugins"])
        self.assertIn("video-frames", profiles["data-ml"]["skills"])


class EnsureProfilesTests(unittest.TestCase):
    def test_bootstraps_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "profiles.json"
            doc, created = apply_profile.ensure_profiles(path)
            self.assertTrue(created)
            self.assertTrue(path.exists())
            self.assertEqual(doc, apply_profile.STARTER_PROFILES)
            self.assertEqual(json.loads(path.read_text()), apply_profile.STARTER_PROFILES)

    def test_existing_file_wins_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profiles.json"
            custom = {"version": 1, "profiles": {"mine": {"description": "x", "skills": [], "plugins": []}}}
            path.write_text(json.dumps(custom))
            doc, created = apply_profile.ensure_profiles(path)
            self.assertFalse(created)
            self.assertEqual(doc, custom)


class AtomicWriteJsonTests(unittest.TestCase):
    def test_writes_json_with_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            apply_profile.atomic_write_json(path, {"a": 1})
            text = path.read_text()
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(json.loads(text), {"a": 1})

    def test_replaces_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            path.write_text("{\"old\": true}")
            apply_profile.atomic_write_json(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"new": True})
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: new tests FAIL with `AttributeError` (`STARTER_PROFILES` etc. undefined); Task 2 tests still PASS.

- [ ] **Step 3: Implement profiles + bootstrap**

In `plugins/plugin-configure/scripts/apply_profile.py`, extend the imports and add below the `_SCOPE_RANK` constant:

```python
import os
import tempfile
from pathlib import Path
```

(merge into the existing import block: final imports are `argparse` [Task 4], `json`, `os`, `subprocess` [Task 4], `sys` [Task 4], `tempfile`, `datetime` [Task 4], `pathlib.Path`)

```python
PROFILES_PATH = Path.home() / ".claude" / "plugin-configure" / "profiles.json"

_GENERAL_SKILLS = [
    "agent-browser", "agent-md-refactor", "caveman", "diagnose", "find-skills",
    "grill-with-docs", "improve-codebase-architecture", "prototype",
    "setup-matt-pocock-skills", "tdd", "tmux", "to-issues", "to-prd", "triage",
    "zoom-out",
]
_GENERAL_PLUGINS = [
    "claude-md-management@claude-plugins-official",
    "code-review@claude-plugins-official",
    "code-simplifier@claude-plugins-official",
    "codex@openai-codex",
    "context7@claude-plugins-official",
    "feature-dev@claude-plugins-official",
    "github@claude-plugins-official",
    "hookify@claude-plugins-official",
    "pr-review-toolkit@claude-plugins-official",
    "remember@claude-plugins-official",
    "security-guidance@claude-plugins-official",
    "superpowers@claude-plugins-official",
]
_WEB_SKILLS = [
    "frontend-design", "react-dev", "react-useeffect",
    "vercel-composition-patterns", "vercel-react-best-practices",
    "vercel-react-native-skills", "web-design-guidelines", "webapp-testing",
]

STARTER_PROFILES = {
    "version": 1,
    "profiles": {
        "general-dev": {
            "description": "Everyday default: core process skills + core tooling plugins",
            "skills": _GENERAL_SKILLS,
            "plugins": _GENERAL_PLUGINS,
        },
        "minimal": {
            "description": "Near-silent: every personal skill off; superpowers + remember only",
            "skills": [],
            "plugins": [
                "remember@claude-plugins-official",
                "superpowers@claude-plugins-official",
            ],
        },
        "web-dev": {
            "description": "general-dev + frontend stack (react/vercel skills, playwright, vercel)",
            "skills": sorted(_GENERAL_SKILLS + _WEB_SKILLS),
            "plugins": sorted(_GENERAL_PLUGINS + [
                "playwright@claude-plugins-official",
                "vercel@claude-plugins-official",
            ]),
        },
        "data-ml": {
            "description": "general-dev + ML tooling (huggingface-skills, video-frames)",
            "skills": sorted(_GENERAL_SKILLS + ["video-frames"]),
            "plugins": sorted(_GENERAL_PLUGINS + [
                "huggingface-skills@claude-plugins-official",
            ]),
        },
    },
}


def atomic_write_json(path, data):
    """Write JSON to path atomically (temp file in same dir + rename).

    Args:
        path: Destination Path; parent directories are created as needed.
        data: JSON-serializable object; written with indent=2 and a trailing
            newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def ensure_profiles(path):
    """Load the profiles document, bootstrapping starters when missing.

    Args:
        path: Path to profiles.json.

    Returns:
        Tuple (profiles_doc, created) where created says whether the starter
        file was written by this call.
    """
    created = False
    if not path.exists():
        atomic_write_json(path, STARTER_PROFILES)
        created = True
    return json.loads(path.read_text()), created
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/plugin-configure/scripts/apply_profile.py plugins/plugin-configure/tests/test_apply_profile.py
git commit -m "add starter profiles and profiles.json bootstrap"
```

---

### Task 4: apply_profile.py IO + CLI (TDD, includes subprocess end-to-end test)

**Files:**
- Modify: `plugins/plugin-configure/scripts/apply_profile.py`
- Test: `plugins/plugin-configure/tests/test_apply_profile.py`

**Interfaces:**
- Consumes: everything from Tasks 2–3.
- Produces:
  - `MARKER_RELPATH = ".claude/plugin-configure.json"` (str constant)
  - `PLUGIN_VERSION = "0.1.0"` (str constant)
  - `find_repo_root(cwd) -> Path | None`
  - `discover_skills(skill_dirs) -> set` — dirs/symlinked-dirs only, dotfiles ignored.
  - `load_plugin_records() -> list | None` — None (with stderr warning) when `claude` is missing/fails/returns non-list.
  - `write_marker(root, marker) -> Path`, `ensure_git_exclude(root) -> None`, `utc_now_iso() -> str`
  - `main(argv=None) -> int` — the CLI contract Tasks 5–6 rely on: `apply_profile.py <profile> | --skip | --bootstrap-only`; exit 0 on success, 2 on user error.

- [ ] **Step 1: Add the failing tests**

Append to `plugins/plugin-configure/tests/test_apply_profile.py` (add `import subprocess` to the top imports; `APPLY = Path(__file__).resolve().parents[1] / "scripts" / "apply_profile.py"` as a module-level constant below the `sys.path` bootstrap):

```python
class DiscoverSkillsTests(unittest.TestCase):
    def test_dirs_and_symlinked_dirs_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills" / "real-skill").mkdir(parents=True)
            (root / "elsewhere" / "linked-skill").mkdir(parents=True)
            (root / "skills" / "linked-skill").symlink_to(root / "elsewhere" / "linked-skill")
            (root / "skills" / ".hidden").mkdir()
            (root / "skills" / "stray-file.md").write_text("not a skill")
            names = apply_profile.discover_skills([root / "skills", root / "missing"])
            self.assertEqual(names, {"real-skill", "linked-skill"})


class GitHelpersTests(unittest.TestCase):
    def _make_repo(self, tmp):
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def test_find_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._make_repo(tmp)
            sub = repo / "a" / "b"
            sub.mkdir(parents=True)
            self.assertEqual(apply_profile.find_repo_root(sub).resolve(), repo.resolve())
            outside = Path(tmp) / "plain"
            outside.mkdir()
            self.assertIsNone(apply_profile.find_repo_root(outside))

    def test_ensure_git_exclude_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._make_repo(tmp)
            apply_profile.ensure_git_exclude(repo)
            apply_profile.ensure_git_exclude(repo)
            exclude = repo / ".git" / "info" / "exclude"
            lines = exclude.read_text().splitlines()
            self.assertEqual(lines.count(apply_profile.MARKER_RELPATH), 1)

    def test_ensure_git_exclude_noop_outside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            apply_profile.ensure_git_exclude(Path(tmp))  # must not raise
            self.assertFalse((Path(tmp) / ".git").exists())


FAKE_PLUGIN_RECORDS = [
    {"id": "keep@m", "enabled": True, "scope": "user"},
    {"id": "drop@m", "enabled": True, "scope": "user"},
    {"id": "wake@m", "enabled": False, "scope": "user"},
    {"id": apply_profile.SELF_PLUGIN_ID, "enabled": True, "scope": "user"},
]


class CliEndToEndTests(unittest.TestCase):
    """Run apply_profile.py as a subprocess against a fake HOME, repo and claude CLI."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.home = tmp / "home"
        for skill in ("alpha-skill", "beta-skill", "kept-skill"):
            (self.home / ".claude" / "skills" / skill).mkdir(parents=True)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        bindir = tmp / "bin"
        bindir.mkdir()
        fake = bindir / "claude"
        fake.write_text("#!/bin/sh\ncat <<'EOF'\n%s\nEOF\n" % json.dumps(FAKE_PLUGIN_RECORDS))
        fake.chmod(0o755)
        profiles = {
            "version": 1,
            "profiles": {
                "test-profile": {
                    "description": "fixture",
                    "skills": ["kept-skill"],
                    "plugins": ["keep@m", "wake@m"],
                }
            },
        }
        profiles_path = self.home / ".claude" / "plugin-configure" / "profiles.json"
        profiles_path.parent.mkdir(parents=True)
        profiles_path.write_text(json.dumps(profiles))
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=f"{bindir}:{os.environ['PATH']}")

    def tearDown(self):
        self._tmp.cleanup()

    def run_apply(self, *args):
        return subprocess.run(
            [sys.executable, str(APPLY), *args],
            cwd=str(self.repo), env=self.env, capture_output=True, text=True,
        )

    def test_apply_profile_writes_everything(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "settings.local.json").write_text(
            json.dumps({"permissions": {"allow": ["Bash(ls *)"]}}))
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads((self.repo / ".claude" / "settings.local.json").read_text())
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls *)"]})
        self.assertEqual(settings["skillOverrides"],
                         {"alpha-skill": "off", "beta-skill": "off"})
        self.assertEqual(settings["disabledPlugins"], ["drop@m"])
        self.assertEqual(settings["enabledPlugins"], ["wake@m"])
        marker = json.loads((self.repo / ".claude" / "plugin-configure.json").read_text())
        self.assertEqual(marker["profile"], "test-profile")
        self.assertIn("appliedAt", marker)
        self.assertEqual(marker["pluginVersion"], apply_profile.PLUGIN_VERSION)
        exclude = (self.repo / ".git" / "info" / "exclude").read_text()
        self.assertIn(apply_profile.MARKER_RELPATH, exclude)

    def test_skip_writes_only_marker(self):
        result = self.run_apply("--skip")
        self.assertEqual(result.returncode, 0, result.stderr)
        marker = json.loads((self.repo / ".claude" / "plugin-configure.json").read_text())
        self.assertTrue(marker["skipped"])
        self.assertFalse((self.repo / ".claude" / "settings.local.json").exists())

    def test_unknown_profile_errors(self):
        result = self.run_apply("nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("test-profile", result.stderr)

    def test_bootstrap_only_lists_profiles(self):
        result = self.run_apply("--bootstrap-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test-profile", result.stdout)
        self.assertFalse((self.repo / ".claude").exists())

    def test_invalid_settings_json_aborts_cleanly(self):
        (self.repo / ".claude").mkdir()
        broken = self.repo / ".claude" / "settings.local.json"
        broken.write_text("{not json")
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(broken.read_text(), "{not json")
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: new tests FAIL (`AttributeError: ... 'discover_skills'` etc.); earlier tests PASS.

- [ ] **Step 3: Implement IO + CLI**

In `plugins/plugin-configure/scripts/apply_profile.py`, complete the import block:

```python
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
```

Add constants next to `SELF_PLUGIN_ID`:

```python
PLUGIN_VERSION = "0.1.0"
MARKER_RELPATH = ".claude/plugin-configure.json"
```

Append below `ensure_profiles`:

```python
def find_repo_root(cwd):
    """Return the git repo root containing cwd, or None outside a repo.

    Args:
        cwd: Directory to resolve from.

    Returns:
        Path of the repo toplevel, or None.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd), capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None
    return Path(out) if out else None


def discover_skills(skill_dirs):
    """Collect skill names from skills directories.

    Args:
        skill_dirs: Iterable of directories to scan; missing ones are skipped.

    Returns:
        Set of names of directories (or symlinks to directories) found,
        ignoring dotfile entries and plain files.
    """
    names = set()
    for skill_dir in skill_dirs:
        if not skill_dir.is_dir():
            continue
        for entry in skill_dir.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                names.add(entry.name)
    return names


def load_plugin_records():
    """Read the installed-plugin inventory from the claude CLI.

    Returns:
        The parsed record list from `claude plugin list --json`, or None when
        the CLI is missing, fails, or returns an unexpected shape (a warning
        is printed to stderr; plugin settings are then left untouched).
    """
    try:
        out = subprocess.run(
            ["claude", "plugin", "list", "--json"],
            capture_output=True, text=True, check=True,
        ).stdout
        records = json.loads(out)
    except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        print(f"warning: could not read plugin inventory ({exc}); "
              "leaving plugin settings untouched", file=sys.stderr)
        return None
    if not isinstance(records, list):
        print("warning: unexpected `claude plugin list --json` output; "
              "leaving plugin settings untouched", file=sys.stderr)
        return None
    return records


def utc_now_iso():
    """Return the current UTC time as an ISO-8601 string (second precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_marker(root, marker):
    """Write the idempotency marker under root.

    Args:
        root: Target root directory (repo root or cwd).
        marker: JSON-serializable marker payload.

    Returns:
        The marker file Path.
    """
    path = root / MARKER_RELPATH
    atomic_write_json(path, marker)
    return path


def ensure_git_exclude(root):
    """Add the marker path to the repo's .git/info/exclude (once).

    No-op outside a git repo. Uses `git rev-parse --git-path` so worktrees
    resolve to the correct exclude file.

    Args:
        root: Directory inside the repo (normally the repo root).
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-path", "info/exclude"],
            cwd=str(root), capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return
    exclude = Path(out)
    if not exclude.is_absolute():
        exclude = root / exclude
    lines = exclude.read_text().splitlines() if exclude.exists() else []
    if MARKER_RELPATH in lines:
        return
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a") as fh:
        fh.write(MARKER_RELPATH + "\n")


def main(argv=None):
    """CLI entry point.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Process exit code: 0 on success, 2 on user error.
    """
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("profile", nargs="?", help="profile name to apply")
    parser.add_argument("--skip", action="store_true",
                        help="record a skip marker and exit")
    parser.add_argument("--bootstrap-only", action="store_true",
                        help="ensure profiles.json exists, list profiles, exit")
    args = parser.parse_args(argv)

    profiles_doc, created = ensure_profiles(PROFILES_PATH)
    profiles = profiles_doc.get("profiles", {})
    if created:
        print(f"bootstrapped starter profiles at {PROFILES_PATH}")

    if args.bootstrap_only:
        for name in sorted(profiles):
            print(f"{name}: {profiles[name].get('description', '')}")
        return 0

    root = find_repo_root(Path.cwd()) or Path.cwd()

    if args.skip:
        marker = write_marker(root, {"skipped": True, "appliedAt": utc_now_iso()})
        ensure_git_exclude(root)
        print(f"skip recorded at {marker}; the session nudge is silenced here")
        return 0

    if not args.profile or args.profile not in profiles:
        names = ", ".join(sorted(profiles))
        print(f"error: unknown profile {args.profile!r}; available: {names}",
              file=sys.stderr)
        return 2

    spec = profiles[args.profile]
    discovered = discover_skills(
        [Path.home() / ".claude" / "skills", root / ".claude" / "skills"])
    overrides = compute_skill_overrides(discovered, spec.get("skills", []))

    records = load_plugin_records()
    if records is None:
        disabled, enabled = [], []
    else:
        disabled, enabled = compute_plugin_arrays(
            effective_plugin_state(records), spec.get("plugins", []))

    settings_path = root / ".claude" / "settings.local.json"
    try:
        existing = (json.loads(settings_path.read_text())
                    if settings_path.exists() else {})
    except json.JSONDecodeError as exc:
        print(f"error: {settings_path} is not valid JSON ({exc}); "
              "fix it and re-run", file=sys.stderr)
        return 2

    atomic_write_json(settings_path, merge_settings(
        existing, overrides, disabled, enabled, records is not None))
    write_marker(root, {"profile": args.profile, "appliedAt": utc_now_iso(),
                        "pluginVersion": PLUGIN_VERSION})
    ensure_git_exclude(root)

    print(f"applied profile {args.profile!r} to {settings_path}")
    print(f"  skills off: {len(overrides)}  plugins disabled: {len(disabled)}"
          f"  plugins enabled: {len(enabled)}")
    print("  takes effect from the next Claude Code session in this directory")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 plugins/plugin-configure/tests/test_apply_profile.py -v`
Expected: all tests PASS (including the five CLI end-to-end tests).

- [ ] **Step 5: Commit**

```bash
git add plugins/plugin-configure/scripts/apply_profile.py plugins/plugin-configure/tests/test_apply_profile.py
git commit -m "add apply_profile.py discovery, settings writing and CLI"
```

---

### Task 5: SessionStart hook (TDD with a shell test script)

**Files:**
- Create: `plugins/plugin-configure/hooks/hooks.json`
- Create: `plugins/plugin-configure/hooks/session-start.sh`
- Test: `plugins/plugin-configure/tests/test_hook.sh`

**Interfaces:**
- Consumes: the marker path `.claude/plugin-configure.json` and the `--skip` CLI from Task 4 (referenced in the nudge text).
- Produces: a SessionStart hook that emits `hookSpecificOutput.additionalContext` JSON telling the model to invoke the `plugin-configure:configure` command (created in Task 6).

- [ ] **Step 1: Write the failing test script**

Create `plugins/plugin-configure/tests/test_hook.sh`:

```bash
#!/bin/bash
# Tests for hooks/session-start.sh. Run: bash plugins/plugin-configure/tests/test_hook.sh
set -u

HOOK="$(cd "$(dirname "$0")/.." && pwd)/hooks/session-start.sh"
fails=0

expect_silent() { # label dir
  out=$(cd "$2" && CLAUDE_PLUGIN_ROOT="/fake/plugin root" bash "$HOOK"; echo "rc=$?")
  if [ "$out" = "rc=0" ]; then echo "PASS: $1"; else echo "FAIL: $1 -> $out"; fails=$((fails + 1)); fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# 1. non-git dir -> silent, exit 0
mkdir "$tmp/plain"
expect_silent "non-git dir is silent" "$tmp/plain"

# 2. unconfigured git repo -> nudge mentioning the configure command
git init -q "$tmp/repo"
out=$(cd "$tmp/repo" && CLAUDE_PLUGIN_ROOT="/fake/plugin root" bash "$HOOK")
case "$out" in
  *hookSpecificOutput*plugin-configure:configure*) echo "PASS: unconfigured repo nudges" ;;
  *) echo "FAIL: unconfigured repo nudges -> $out"; fails=$((fails + 1)) ;;
esac

# 3. nudge output is valid JSON and carries the plugin root path
echo "$out" | python3 -c '
import json, sys
doc = json.load(sys.stdin)
ctx = doc["hookSpecificOutput"]["additionalContext"]
assert doc["hookSpecificOutput"]["hookEventName"] == "SessionStart", "wrong event"
assert "/fake/plugin root" in ctx, "plugin root missing from context"
' && echo "PASS: nudge is valid JSON with plugin root" || { echo "FAIL: nudge is valid JSON with plugin root"; fails=$((fails + 1)); }

# 4. marker file -> silent
mkdir -p "$tmp/repo/.claude"
echo '{"skipped": true}' > "$tmp/repo/.claude/plugin-configure.json"
expect_silent "marker silences the hook" "$tmp/repo"
rm "$tmp/repo/.claude/plugin-configure.json"

# 5. existing skillOverrides -> silent (grandfathered hand-curated repo)
echo '{"skillOverrides": {"x": "off"}}' > "$tmp/repo/.claude/settings.local.json"
expect_silent "skillOverrides silences the hook" "$tmp/repo"

echo "---"
if [ "$fails" -eq 0 ]; then echo "ALL PASS"; else echo "$fails FAILURE(S)"; fi
exit "$fails"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash plugins/plugin-configure/tests/test_hook.sh`
Expected: FAILs (hook script doesn't exist yet; bash reports "No such file").

- [ ] **Step 3: Implement the hook script and hooks.json**

Create `plugins/plugin-configure/hooks/session-start.sh`:

```bash
#!/bin/bash
# SessionStart nudge: offer a profile pick in unconfigured git repos.
# Every non-nudge path exits 0 silently -- this hook must never block a session.

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$root" ] || exit 0
[ -e "$root/.claude/plugin-configure.json" ] && exit 0
settings="$root/.claude/settings.local.json"
if [ -f "$settings" ] && grep -q '"skillOverrides"' "$settings"; then
  exit 0
fi

cat <<JSON
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "plugin-configure: this repo has no skill/plugin profile applied. After handling the user's immediate request (or right away if there is none), invoke the plugin-configure:configure command via the Skill tool to offer a one-card profile pick. If the user declines, silence this nudge permanently for this repo by running: python3 \\"${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py\\" --skip"}}
JSON
exit 0
```

Create `plugins/plugin-configure/hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

(No `matcher`: fires on every SessionStart source — startup/resume/clear/compact. The marker and skillOverrides checks make repeat fires silent, so the worst case is one duplicate nudge line after a compact in a still-undecided repo.)

- [ ] **Step 4: Run the hook tests to verify they pass**

Run: `bash plugins/plugin-configure/tests/test_hook.sh`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Validate the plugin still parses**

Run: `claude plugin validate plugins/plugin-configure`
Expected: valid (hooks.json schema accepted).

- [ ] **Step 6: Commit**

```bash
git add plugins/plugin-configure/hooks/ plugins/plugin-configure/tests/test_hook.sh
git commit -m "add SessionStart nudge hook with shell tests"
```

---

### Task 6: configure command + plugin README

**Files:**
- Create: `plugins/plugin-configure/commands/configure.md`
- Create: `plugins/plugin-configure/README.md`

**Interfaces:**
- Consumes: the `apply_profile.py` CLI contract from Task 4 (`--bootstrap-only`, `<profile>`, `--skip`) and the hook nudge text from Task 5 (which names `plugin-configure:configure`).
- Produces: the `/plugin-configure:configure` slash command — the single interactive flow used both by the nudge and manually.

- [ ] **Step 1: Write the command**

Create `plugins/plugin-configure/commands/configure.md`:

```markdown
---
description: Apply a skill/plugin profile to this repo's .claude/settings.local.json (or re-apply / skip)
---

Apply a curated skill/plugin profile to the current repo's local settings.
Follow these steps exactly:

1. Run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" --bootstrap-only`
   It prints one `name: description` line per available profile (bootstrapping
   `~/.claude/plugin-configure/profiles.json` with starter profiles on first
   run).

2. Present ONE AskUserQuestion card asking which profile to apply: one option
   per profile (label = profile name, description = its description line), max
   4 options. If there are more than 4 profiles, prefer `general-dev`,
   `minimal`, `web-dev`, `data-ml` and mention the rest in the question text
   (reachable via "Other"). The automatic "Other" option doubles as the skip
   path — mention that in the question text.

3. Act on the answer:
   - A profile name (picked or typed): run
     `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" <profile>`
   - "Other" with skip-like text, a dismissal, or an explicit decline: run
     `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_profile.py" --skip`

4. Relay the script's summary (skills turned off, plugins disabled/enabled,
   file paths) and remind the user the new settings take effect from the next
   Claude Code session in this directory — the current session keeps its
   already-loaded skills. Profiles can be edited any time at
   `~/.claude/plugin-configure/profiles.json`; re-running this command
   re-applies over the previous choice.
```

- [ ] **Step 2: Write the plugin README**

Create `plugins/plugin-configure/README.md`:

```markdown
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
```

- [ ] **Step 3: Validate and run everything**

Run:
```bash
claude plugin validate plugins/plugin-configure && claude plugin validate .
python3 plugins/plugin-configure/tests/test_apply_profile.py -v
bash plugins/plugin-configure/tests/test_hook.sh
```
Expected: validate clean; all python tests PASS; hook tests ALL PASS.

- [ ] **Step 4: Commit**

```bash
git add plugins/plugin-configure/commands/configure.md plugins/plugin-configure/README.md
git commit -m "add configure command and plugin README"
```

---

### Task 7: Real-environment verification

**Files:**
- No new files (scratch dirs only; use a temp dir OUTSIDE the repo).

**Interfaces:**
- Consumes: the finished plugin from Tasks 1–6.
- Produces: verified behavior in the real environment + a short handoff note for the one step that needs an interactive session.

- [ ] **Step 1: Verify the real bootstrap + real inventories (safe: touches only `~/.claude/plugin-configure/`)**

```bash
python3 plugins/plugin-configure/scripts/apply_profile.py --bootstrap-only
```
Expected: prints `bootstrapped starter profiles at /Users/ooj/.claude/plugin-configure/profiles.json` (first run only) then the four `name: description` lines. Check the file exists and lists 4 profiles.

- [ ] **Step 2: Apply a profile to a scratch repo for real**

```bash
scratch=$(mktemp -d)
git init -q "$scratch"
cd "$scratch"
bash /Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/plugins/plugin-configure/hooks/session-start.sh
python3 /Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/plugins/plugin-configure/scripts/apply_profile.py general-dev
bash /Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/plugins/plugin-configure/hooks/session-start.sh
cat .claude/settings.local.json | python3 -m json.tool | head -40
cat .claude/plugin-configure.json
cat .git/info/exclude
cd /Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure
```
Expected: first hook run prints the nudge JSON; the script reports ~27 skills off and real plugin counts; second hook run prints nothing; settings/marker/exclude all as designed (with the REAL 42-skill inventory: `skillOverrides` has 42 − 15 = 27 entries for general-dev).

- [ ] **Step 3: Verify ooj-tools itself is grandfathered**

```bash
cd /Users/ooj/Fun/code/ooj-tools && bash .claude/worktrees/plugin-configure/plugins/plugin-configure/hooks/session-start.sh; cd -
```
Expected: no output, exit 0 (main checkout's `.claude/settings.local.json` already has `skillOverrides`).

- [ ] **Step 4: Interactive check (hand to the user)**

Report to the user that everything scripted passes, then ask them to run the one thing that needs a live session:

```
cd $(mktemp -d) && git init -q . && claude --plugin-dir /Users/ooj/Fun/code/ooj-tools/.claude/worktrees/plugin-configure/plugins/plugin-configure
```
and confirm: (a) the profile card appears, (b) picking `minimal` writes the files, (c) relaunching shows no nudge and a smaller `/context`.

- [ ] **Step 5: Final commit (if verification produced fixes)**

Commit any fixes uncovered by verification with a message describing the fix; otherwise nothing to commit.

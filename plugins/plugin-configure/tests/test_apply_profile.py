#!/usr/bin/env python3
"""Tests for scripts/apply_profile.py. Run: python3 plugins/plugin-configure/tests/test_apply_profile.py -v"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
APPLY = Path(__file__).resolve().parents[1] / "scripts" / "apply_profile.py"
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


if __name__ == "__main__":
    unittest.main()

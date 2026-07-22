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

SELF_ID = f"{apply_profile.SELF_PLUGIN_NAME}@ooj-tools"


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

    def test_managed_beats_local(self):
        records = [
            {"id": "a@m", "enabled": True, "scope": "local"},
            {"id": "a@m", "enabled": False, "scope": "managed"},
        ]
        self.assertEqual(apply_profile.effective_plugin_state(records), {"a@m": False})

    def test_record_without_id_is_ignored(self):
        records = [{"enabled": True, "scope": "user"}]
        self.assertEqual(apply_profile.effective_plugin_state(records), {})


class BaselinePluginStateTests(unittest.TestCase):
    def test_local_scope_is_ignored(self):
        records = [
            {"id": "a@m", "enabled": True, "scope": "user"},
            {"id": "a@m", "enabled": False, "scope": "local"},
        ]
        self.assertEqual(apply_profile.baseline_plugin_state(records), {"a@m": True})

    def test_local_only_plugin_falls_back_to_local_state(self):
        records = [{"id": "a@m", "enabled": False, "scope": "local"}]
        self.assertEqual(apply_profile.baseline_plugin_state(records), {"a@m": False})

    def test_mixed_local_and_non_local(self):
        records = [
            {"id": "a@m", "enabled": True, "scope": "user"},
            {"id": "a@m", "enabled": False, "scope": "local"},
            {"id": "b@m", "enabled": True, "scope": "local"},
        ]
        self.assertEqual(apply_profile.baseline_plugin_state(records),
                         {"a@m": True, "b@m": True})


class IsSelfTests(unittest.TestCase):
    def test_matches_any_marketplace(self):
        self.assertTrue(apply_profile._is_self("plugin-configure@ooj-tools"))
        self.assertTrue(apply_profile._is_self("plugin-configure@dev-dir"))

    def test_rejects_other_plugins(self):
        self.assertFalse(apply_profile._is_self("other@ooj-tools"))
        self.assertFalse(apply_profile._is_self("plugin-configure-extra@m"))


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


class ComputeEnabledPluginsTests(unittest.TestCase):
    def test_enabled_unlisted_gets_disabled(self):
        baseline = {"a@m": True, "b@m": True}
        self.assertEqual(
            apply_profile.compute_enabled_plugins(baseline, ["a@m"]),
            {"b@m": False})

    def test_matching_state_writes_no_entry(self):
        baseline = {"a@m": True, "b@m": False}
        self.assertEqual(apply_profile.compute_enabled_plugins(baseline, ["a@m"]), {})

    def test_listed_but_disabled_gets_enabled(self):
        baseline = {"a@m": False}
        self.assertEqual(
            apply_profile.compute_enabled_plugins(baseline, ["a@m"]), {"a@m": True})

    def test_listed_but_not_installed_is_ignored(self):
        self.assertEqual(apply_profile.compute_enabled_plugins({}, ["ghost@m"]), {})

    def test_self_is_never_disabled(self):
        baseline = {SELF_ID: True, "b@m": True}
        self.assertEqual(
            apply_profile.compute_enabled_plugins(baseline, []), {"b@m": False})

    def test_self_under_dev_marketplace_is_protected_too(self):
        baseline = {"plugin-configure@dev-dir": True}
        self.assertEqual(apply_profile.compute_enabled_plugins(baseline, []), {})

    def test_self_not_force_enabled_unless_listed(self):
        self.assertEqual(
            apply_profile.compute_enabled_plugins({SELF_ID: False}, []), {})
        self.assertEqual(
            apply_profile.compute_enabled_plugins({SELF_ID: False}, [SELF_ID]),
            {SELF_ID: True})

    def test_output_is_sorted_by_id(self):
        baseline = {"z@m": True, "a@m": True, "m@m": False}
        result = apply_profile.compute_enabled_plugins(baseline, ["m@m"])
        self.assertEqual(list(result), ["a@m", "m@m", "z@m"])


class MergeSettingsTests(unittest.TestCase):
    def test_foreign_keys_survive(self):
        existing = {"permissions": {"allow": ["Bash(ls *)"]}}
        merged = apply_profile.merge_settings(
            existing, {"a": "off"}, {"p@m": False}, True)
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls *)"]})
        self.assertEqual(merged["skillOverrides"], {"a": "off"})
        self.assertEqual(merged["enabledPlugins"], {"p@m": False})

    def test_old_overrides_replaced_wholesale(self):
        existing = {"skillOverrides": {"stale": "off"}}
        merged = apply_profile.merge_settings(existing, {"fresh": "off"}, {}, True)
        self.assertEqual(merged["skillOverrides"], {"fresh": "off"})

    def test_empty_skill_overrides_still_written(self):
        merged = apply_profile.merge_settings({}, {}, {}, True)
        self.assertEqual(merged["skillOverrides"], {})

    def test_empty_plugin_map_removes_stale_key(self):
        existing = {"enabledPlugins": {"old@m": False}}
        merged = apply_profile.merge_settings(existing, {}, {}, True)
        self.assertNotIn("enabledPlugins", merged)

    def test_legacy_disabled_plugins_key_is_dropped(self):
        existing = {"disabledPlugins": ["old@m"]}
        merged = apply_profile.merge_settings(existing, {}, {"a@m": True}, True)
        self.assertNotIn("disabledPlugins", merged)
        self.assertEqual(merged["enabledPlugins"], {"a@m": True})

    def test_plugins_unknown_leaves_plugin_keys_untouched(self):
        existing = {"enabledPlugins": {"keep@m": False},
                    "disabledPlugins": ["legacy@m"]}
        merged = apply_profile.merge_settings(existing, {}, {}, False)
        self.assertEqual(merged["enabledPlugins"], {"keep@m": False})
        self.assertEqual(merged["disabledPlugins"], ["legacy@m"])

    def test_existing_dict_not_mutated(self):
        existing = {"skillOverrides": {"stale": "off"}}
        apply_profile.merge_settings(existing, {"fresh": "off"}, {}, True)
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

    def test_ensure_git_exclude_handles_missing_trailing_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._make_repo(tmp)
            exclude = repo / ".git" / "info" / "exclude"
            exclude.parent.mkdir(parents=True, exist_ok=True)
            exclude.write_text("# comment without newline")
            apply_profile.ensure_git_exclude(repo)
            lines = exclude.read_text().splitlines()
            self.assertIn("# comment without newline", lines)
            self.assertIn(apply_profile.MARKER_RELPATH, lines)


FAKE_PLUGIN_RECORDS = [
    {"id": "keep@m", "enabled": True, "scope": "user"},
    {"id": "drop@m", "enabled": True, "scope": "user"},
    {"id": "wake@m", "enabled": False, "scope": "user"},
    {"id": SELF_ID, "enabled": True, "scope": "user"},
]

PROFILES_FIXTURE = {
    "version": 1,
    "profiles": {
        "test-profile": {
            "description": "fixture",
            "skills": ["kept-skill"],
            "plugins": ["keep@m", "wake@m"],
        },
        "other-profile": {
            "description": "fixture 2",
            "skills": ["alpha-skill"],
            "plugins": ["drop@m"],
        },
        "everything": {
            "description": "keeps all fixture skills and plugins",
            "skills": ["alpha-skill", "beta-skill", "kept-skill"],
            "plugins": ["drop@m", "keep@m", "wake@m"],
        },
    },
}


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
        self.bindir = tmp / "bin"
        self.bindir.mkdir()
        self._install_fake_claude(
            "#!/bin/sh\ncat <<'EOF'\n%s\nEOF\n" % json.dumps(FAKE_PLUGIN_RECORDS))
        profiles_path = self.home / ".claude" / "plugin-configure" / "profiles.json"
        profiles_path.parent.mkdir(parents=True)
        profiles_path.write_text(json.dumps(PROFILES_FIXTURE))
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=f"{self.bindir}:{os.environ['PATH']}")

    def tearDown(self):
        self._tmp.cleanup()

    def _install_fake_claude(self, script):
        fake = self.bindir / "claude"
        fake.write_text(script)
        fake.chmod(0o755)

    def run_apply(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(APPLY), *args],
            cwd=str(cwd or self.repo), env=self.env, capture_output=True, text=True,
        )

    def read_settings(self, root=None):
        path = (root or self.repo) / ".claude" / "settings.local.json"
        return json.loads(path.read_text())

    def read_marker(self, root=None):
        path = (root or self.repo) / ".claude" / "plugin-configure.json"
        return json.loads(path.read_text())

    def test_apply_profile_writes_everything(self):
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "settings.local.json").write_text(
            json.dumps({"permissions": {"allow": ["Bash(ls *)"]}}))
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.read_settings()
        self.assertEqual(settings["permissions"], {"allow": ["Bash(ls *)"]})
        self.assertEqual(settings["skillOverrides"],
                         {"alpha-skill": "off", "beta-skill": "off"})
        self.assertEqual(settings["enabledPlugins"],
                         {"drop@m": False, "wake@m": True})
        self.assertNotIn("disabledPlugins", settings)
        marker = self.read_marker()
        self.assertEqual(marker["profile"], "test-profile")
        self.assertIn("appliedAt", marker)
        self.assertEqual(marker["pluginVersion"], apply_profile.PLUGIN_VERSION)
        exclude = (self.repo / ".git" / "info" / "exclude").read_text()
        self.assertIn(apply_profile.MARKER_RELPATH, exclude)

    def test_reapply_same_profile_is_idempotent(self):
        self.assertEqual(self.run_apply("test-profile").returncode, 0)
        first = self.read_settings()
        self.assertEqual(self.run_apply("test-profile").returncode, 0)
        self.assertEqual(self.read_settings(), first)
        self.assertEqual(first["enabledPlugins"], {"drop@m": False, "wake@m": True})

    def test_profile_switch_replaces_owned_keys_wholesale(self):
        self.assertEqual(self.run_apply("test-profile").returncode, 0)
        self.assertEqual(self.run_apply("other-profile").returncode, 0)
        settings = self.read_settings()
        self.assertEqual(settings["skillOverrides"],
                         {"beta-skill": "off", "kept-skill": "off"})
        self.assertEqual(settings["enabledPlugins"], {"keep@m": False})
        self.assertEqual(self.read_marker()["profile"], "other-profile")

    def test_profile_matching_current_state_writes_empty_overrides(self):
        result = self.run_apply("everything")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.read_settings()
        # Empty but present: the key's presence marks the repo as configured.
        self.assertEqual(settings["skillOverrides"], {})
        self.assertEqual(settings["enabledPlugins"], {"wake@m": True})

    def test_broken_claude_cli_leaves_plugin_settings_untouched(self):
        self._install_fake_claude("#!/bin/sh\nexit 1\n")
        (self.repo / ".claude").mkdir()
        (self.repo / ".claude" / "settings.local.json").write_text(json.dumps(
            {"enabledPlugins": {"x@m": False}, "disabledPlugins": ["legacy@m"]}))
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("could not read plugin inventory", result.stderr)
        self.assertIn("left untouched", result.stdout)
        settings = self.read_settings()
        self.assertEqual(settings["enabledPlugins"], {"x@m": False})
        self.assertEqual(settings["disabledPlugins"], ["legacy@m"])
        self.assertEqual(settings["skillOverrides"],
                         {"alpha-skill": "off", "beta-skill": "off"})

    def test_claude_cli_garbage_output_leaves_plugin_settings_untouched(self):
        self._install_fake_claude("#!/bin/sh\necho not-json\n")
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("could not read plugin inventory", result.stderr)
        self.assertNotIn("enabledPlugins", self.read_settings())

    def test_claude_cli_non_list_output_leaves_plugin_settings_untouched(self):
        self._install_fake_claude("#!/bin/sh\necho '{\"plugins\": []}'\n")
        result = self.run_apply("test-profile")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unexpected", result.stderr)
        self.assertNotIn("enabledPlugins", self.read_settings())

    def test_skip_writes_only_marker(self):
        result = self.run_apply("--skip")
        self.assertEqual(result.returncode, 0, result.stderr)
        marker = self.read_marker()
        self.assertTrue(marker["skipped"])
        self.assertEqual(marker["pluginVersion"], apply_profile.PLUGIN_VERSION)
        self.assertFalse((self.repo / ".claude" / "settings.local.json").exists())

    def test_skip_then_apply_overwrites_marker(self):
        self.assertEqual(self.run_apply("--skip").returncode, 0)
        self.assertEqual(self.run_apply("test-profile").returncode, 0)
        marker = self.read_marker()
        self.assertNotIn("skipped", marker)
        self.assertEqual(marker["profile"], "test-profile")

    def test_apply_outside_git_repo_writes_under_cwd(self):
        plain = Path(self._tmp.name) / "plain"
        plain.mkdir()
        result = self.run_apply("test-profile", cwd=plain)
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = self.read_settings(root=plain)
        self.assertEqual(settings["skillOverrides"],
                         {"alpha-skill": "off", "beta-skill": "off"})
        self.assertEqual(self.read_marker(root=plain)["profile"], "test-profile")
        self.assertFalse((plain / ".git").exists())

    def test_unknown_profile_errors(self):
        result = self.run_apply("nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("test-profile", result.stderr)

    def test_no_arguments_errors(self):
        result = self.run_apply()
        self.assertEqual(result.returncode, 2)
        self.assertIn("available", result.stderr)

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
        self.assertFalse(
            (self.repo / ".claude" / "plugin-configure.json").exists())


if __name__ == "__main__":
    unittest.main()

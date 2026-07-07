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

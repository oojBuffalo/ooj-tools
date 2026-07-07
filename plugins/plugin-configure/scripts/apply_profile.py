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

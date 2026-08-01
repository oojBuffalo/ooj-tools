#!/usr/bin/env python3
"""Apply a curated skill/plugin profile to local Claude Code settings.

Usage:
    apply_profile.py <profile>          Apply a named profile to the current repo/dir.
    apply_profile.py --skip             Record a skip marker only.
    apply_profile.py --bootstrap-only   Ensure profiles.json exists and list profiles.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Imports deliberately keep the former public function names available to
# callers while their implementations live in focused modules.
from json_io import JSON_READ_ERRORS, atomic_write_json
from plugin_inventory import (
    SELF_PLUGIN_NAME,
    PluginId,
    PluginInventoryFormatError,
    PluginRecord,
    PluginScope,
    compute_enabled_plugins,
    effective_plugin_state,
    is_self_plugin,
    load_plugin_records,
    parse_plugin_records,
    records_for_repo,
    summarize_plugin_changes,
)
from profiles import STARTER_PROFILES, ensure_profiles, valid_profiles
from repository_settings import (
    MARKER_RELPATH,
    compute_skill_overrides,
    discover_skills,
    ensure_git_exclude,
    find_repo_root,
    load_settings,
    merge_settings,
    write_marker,
    write_settings,
)


PLUGIN_VERSION = "0.1.0"
PROFILES_PATH = Path.home() / ".claude" / "plugin-configure" / "profiles.json"
_is_self = is_self_plugin


def utc_now_iso():
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("profile", nargs="?", help="profile name to apply")
    parser.add_argument("--skip", action="store_true",
                        help="record a skip marker and exit")
    parser.add_argument("--bootstrap-only", action="store_true",
                        help="ensure profiles.json exists, list profiles, exit")
    return parser.parse_args(argv)


def _load_profiles():
    try:
        profiles_doc, created = ensure_profiles(PROFILES_PATH)
    except JSON_READ_ERRORS as exc:
        print(f"error: could not read {PROFILES_PATH} ({exc}); "
              "fix it and re-run", file=sys.stderr)
        return None

    profiles = (profiles_doc.get("profiles")
                if isinstance(profiles_doc, dict) else None)
    if not valid_profiles(profiles):
        print(f"error: {PROFILES_PATH} has an unexpected structure — "
              'expected {"profiles": {<name>: {"skills": [...], '
              '"plugins": [...]}}}; fix it and re-run', file=sys.stderr)
        return None
    if created:
        print(f"bootstrapped starter profiles at {PROFILES_PATH}")
    return profiles


def _load_existing_settings(settings_path):
    try:
        existing = load_settings(settings_path)
    except JSON_READ_ERRORS as exc:
        print(f"error: could not read {settings_path} ({exc}); "
              "fix it and re-run", file=sys.stderr)
        return None
    if not isinstance(existing, dict):
        print(f"error: {settings_path} is not a JSON object; "
              "fix it and re-run", file=sys.stderr)
        return None
    return existing


def _record_skip(root):
    marker = write_marker(root, {
        "skipped": True,
        "appliedAt": utc_now_iso(),
        "pluginVersion": PLUGIN_VERSION,
    })
    ensure_git_exclude(root)
    print(f"skip recorded at {marker}; the session nudge is silenced here")


def _apply_profile(root, profile_name, spec):
    discovered = discover_skills(
        [Path.home() / ".claude" / "skills", root / ".claude" / "skills"])
    overrides = compute_skill_overrides(discovered, spec.get("skills", []))

    settings_path = root / ".claude" / "settings.local.json"
    existing = _load_existing_settings(settings_path)
    if existing is None:
        return 2
    current_local = existing.get("enabledPlugins")
    if not isinstance(current_local, dict):
        current_local = {}

    records = load_plugin_records(root)
    enabled_plugins = (
        {} if records is None else
        compute_enabled_plugins(records, spec.get("plugins", []), current_local)
    )
    write_settings(settings_path, merge_settings(
        existing, overrides, enabled_plugins, records is not None))
    write_marker(root, {
        "profile": profile_name,
        "appliedAt": utc_now_iso(),
        "pluginVersion": PLUGIN_VERSION,
    })
    ensure_git_exclude(root)

    if records is None:
        plugin_note = "plugins: left untouched (inventory unavailable)"
    else:
        off_count, on_count = summarize_plugin_changes(records, enabled_plugins)
        plugin_note = (f"plugins disabled: {off_count}"
                       f"  plugins enabled: {on_count}")
    print(f"applied profile {profile_name!r} to {settings_path}")
    print(f"  skills off: {len(overrides)}  {plugin_note}")
    print("  takes effect from the next Claude Code session in this directory")
    return 0


def main(argv=None):
    """CLI entry point; return 0 on success or 2 on user-fixable input errors."""
    args = _parse_args(argv)
    root = find_repo_root(Path.cwd()) or Path.cwd()

    if args.skip:
        _record_skip(root)
        return 0

    profiles = _load_profiles()
    if profiles is None:
        return 2
    if args.bootstrap_only:
        for name in sorted(profiles):
            print(f"{name}: {profiles[name].get('description', '')}")
        return 0
    if not args.profile or args.profile not in profiles:
        names = ", ".join(sorted(profiles))
        print(f"error: unknown profile {args.profile!r}; available: {names}",
              file=sys.stderr)
        return 2
    return _apply_profile(root, args.profile, profiles[args.profile])


if __name__ == "__main__":
    sys.exit(main())

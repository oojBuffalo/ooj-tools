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

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SELF_PLUGIN_ID = "plugin-configure@ooj-tools"
PLUGIN_VERSION = "0.1.0"
MARKER_RELPATH = ".claude/plugin-configure.json"

_SCOPE_RANK = {"user": 1, "project": 2, "local": 3}

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


if __name__ == "__main__":
    sys.exit(main())

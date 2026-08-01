"""Repository discovery and settings/marker persistence."""

import subprocess
from pathlib import Path

from json_io import atomic_write_json, read_json


MARKER_RELPATH = ".claude/plugin-configure.json"


def find_repo_root(cwd):
    """Return the git repository containing cwd, or None outside git."""
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd), capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError, UnicodeError):
        return None
    return Path(output) if output else None


def discover_skills(skill_dirs):
    """Return visible directory names found under the supplied skill roots."""
    names = set()
    for skill_dir in skill_dirs:
        if not skill_dir.is_dir():
            continue
        for entry in skill_dir.iterdir():
            if not entry.name.startswith(".") and entry.is_dir():
                names.add(entry.name)
    return names


def compute_skill_overrides(discovered, allowed):
    """Turn off every discovered skill outside the profile allowlist."""
    allowed_set = set(allowed)
    return {name: "off" for name in sorted(discovered) if name not in allowed_set}


def load_settings(path):
    """Return the existing settings document, or an empty object if absent."""
    return read_json(path) if path.exists() else {}


def merge_settings(existing, overrides, enabled_plugins, plugins_known):
    """Replace profile-owned settings keys while preserving all other keys."""
    merged = dict(existing)
    merged["skillOverrides"] = dict(overrides)
    if plugins_known:
        if enabled_plugins:
            merged["enabledPlugins"] = dict(enabled_plugins)
        else:
            merged.pop("enabledPlugins", None)
        merged.pop("disabledPlugins", None)
    return merged


def write_settings(path, settings):
    """Atomically persist a settings document."""
    atomic_write_json(path, settings)


def write_marker(root, marker):
    """Atomically persist the per-repository idempotency marker."""
    path = root / MARKER_RELPATH
    atomic_write_json(path, marker)
    return path


def ensure_git_exclude(root):
    """Add the marker path to this checkout's git info/exclude file once."""
    try:
        output = subprocess.run(
            ["git", "rev-parse", "--git-path", "info/exclude"],
            cwd=str(root), capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError, UnicodeError):
        return

    exclude = Path(output)
    if not exclude.is_absolute():
        exclude = root / exclude
    try:
        text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    except (OSError, UnicodeError):
        return
    if MARKER_RELPATH in text.splitlines():
        return

    exclude.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if not text or text.endswith("\n") else "\n"
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write(prefix + MARKER_RELPATH + "\n")

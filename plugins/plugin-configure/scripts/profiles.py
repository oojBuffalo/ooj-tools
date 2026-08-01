"""Profile defaults, validation, and persistent storage."""

from plugin_inventory import PluginId, PluginInventoryFormatError
from json_io import atomic_write_json, read_json


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
            "description": (
                "general-dev + frontend stack "
                "(react/vercel skills, playwright, vercel)"),
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


def valid_profiles(profiles):
    """Return whether a profiles mapping has the supported schema."""
    if not isinstance(profiles, dict):
        return False
    for name, spec in profiles.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            return False
        if not isinstance(spec.get("description", ""), str):
            return False
        skills = spec.get("skills", [])
        plugins = spec.get("plugins", [])
        if (not isinstance(skills, list)
                or not all(isinstance(skill, str) for skill in skills)
                or not isinstance(plugins, list)):
            return False
        try:
            for plugin_id in plugins:
                PluginId.parse(plugin_id)
        except PluginInventoryFormatError:
            return False
    return True


def ensure_profiles(path):
    """Load profiles, atomically bootstrapping the starter document if absent."""
    created = False
    if not path.exists():
        atomic_write_json(path, STARTER_PROFILES)
        created = True
    return read_json(path), created

"""Typed Claude plugin inventory parsing and local-state reconciliation."""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


SELF_PLUGIN_NAME = "plugin-configure"


class PluginInventoryFormatError(ValueError):
    """Raised when the Claude CLI returns an invalid inventory record."""


@dataclass(frozen=True, order=True)
class PluginId:
    """A validated name@marketplace plugin identity."""

    name: str
    marketplace: str

    @classmethod
    def parse(cls, raw):
        if not isinstance(raw, str):
            raise PluginInventoryFormatError("plugin id must be a string")
        if raw != raw.strip() or raw.count("@") != 1:
            raise PluginInventoryFormatError(
                "plugin id must have the form name@marketplace")
        name, marketplace = raw.split("@", 1)
        if not name or not marketplace:
            raise PluginInventoryFormatError(
                "plugin id must have the form name@marketplace")
        return cls(name=name, marketplace=marketplace)

    def __str__(self):
        return f"{self.name}@{self.marketplace}"


class PluginScope(str, Enum):
    USER = "user"
    PROJECT = "project"
    LOCAL = "local"
    MANAGED = "managed"


_SCOPE_RANK = {
    PluginScope.USER: 1,
    PluginScope.PROJECT: 2,
    PluginScope.LOCAL: 3,
    PluginScope.MANAGED: 4,
}


@dataclass(frozen=True)
class PluginRecord:
    """One validated inventory record emitted by the Claude CLI."""

    plugin_id: PluginId
    enabled: bool
    scope: PluginScope
    project_path: Path = None

    @classmethod
    def parse(cls, raw):
        if not isinstance(raw, dict):
            raise PluginInventoryFormatError("record must be an object")
        plugin_id = PluginId.parse(raw.get("id"))
        enabled = raw.get("enabled")
        if type(enabled) is not bool:
            raise PluginInventoryFormatError("record enabled must be a boolean")
        raw_scope = raw.get("scope")
        try:
            scope = PluginScope(raw_scope)
        except (TypeError, ValueError):
            raise PluginInventoryFormatError(
                "record scope must be user, project, local, or managed")

        raw_project_path = raw.get("projectPath")
        if raw_project_path is not None and (
                not isinstance(raw_project_path, str) or not raw_project_path):
            raise PluginInventoryFormatError(
                "record projectPath must be a non-empty string")
        if scope is PluginScope.PROJECT and raw_project_path is None:
            raise PluginInventoryFormatError(
                "project record must include projectPath")
        project_path = Path(raw_project_path) if raw_project_path is not None else None
        return cls(plugin_id, enabled, scope, project_path)

    def to_json(self):
        """Return the CLI-shaped representation (primarily useful to tests)."""
        raw = {
            "id": str(self.plugin_id),
            "enabled": self.enabled,
            "scope": self.scope.value,
        }
        if self.project_path is not None:
            raw["projectPath"] = str(self.project_path)
        return raw


def parse_plugin_records(raw_records):
    """Parse and validate a complete CLI inventory response."""
    if not isinstance(raw_records, list):
        raise PluginInventoryFormatError("inventory must be a list")
    records = []
    for index, raw_record in enumerate(raw_records):
        try:
            records.append(PluginRecord.parse(raw_record))
        except PluginInventoryFormatError as exc:
            raise PluginInventoryFormatError(f"record {index}: {exc}")
    return tuple(records)


def _canonical_path(path):
    return os.path.normcase(os.path.realpath(os.fspath(path)))


def records_for_repo(records, root):
    """Discard project installations belonging to repositories other than root."""
    target = _canonical_path(root)
    return tuple(
        record for record in records
        if record.scope is not PluginScope.PROJECT
        or _canonical_path(record.project_path) == target
    )


def load_plugin_records(root):
    """Read, validate, and repository-filter the Claude plugin inventory."""
    try:
        output = subprocess.run(
            ["claude", "plugin", "list", "--json"],
            capture_output=True, text=True, check=True,
        ).stdout
        raw_records = json.loads(output)
        records = parse_plugin_records(raw_records)
    except (subprocess.CalledProcessError, OSError, UnicodeError,
            json.JSONDecodeError, RecursionError) as exc:
        print(f"warning: could not read plugin inventory ({exc}); "
              "leaving plugin settings untouched", file=sys.stderr)
        return None
    except PluginInventoryFormatError as exc:
        print("warning: unexpected `claude plugin list --json` output "
              f"({exc}); leaving plugin settings untouched", file=sys.stderr)
        return None
    return records_for_repo(records, root)


def _effective_plugin_state(records):
    best = {}
    for record in records:
        rank = _SCOPE_RANK[record.scope]
        current = best.get(record.plugin_id)
        if current is None or rank > current[0]:
            best[record.plugin_id] = (rank, record.enabled)
    return {plugin_id: enabled for plugin_id, (_, enabled) in best.items()}


def effective_plugin_state(records):
    """Return effective state by plugin id; retained as a simple public view."""
    state = _effective_plugin_state(records)
    return {str(plugin_id): enabled for plugin_id, enabled in state.items()}


def is_self_plugin(plugin_id):
    """Return whether a PluginId (or string id) identifies plugin-configure."""
    if not isinstance(plugin_id, PluginId):
        try:
            plugin_id = PluginId.parse(plugin_id)
        except PluginInventoryFormatError:
            return False
    return plugin_id.name == SELF_PLUGIN_NAME


def _parse_pinned_plugins(current_local):
    pinned = {}
    if not isinstance(current_local, dict):
        return pinned
    for raw_plugin_id, enabled in current_local.items():
        if type(enabled) is not bool:
            continue
        try:
            pinned[PluginId.parse(raw_plugin_id)] = enabled
        except PluginInventoryFormatError:
            continue
    return pinned


def _parse_allowed_plugins(allowed):
    return {plugin_id if isinstance(plugin_id, PluginId) else PluginId.parse(plugin_id)
            for plugin_id in allowed}


def compute_enabled_plugins(records, allowed, current_local=None):
    """Build the explicit local enabledPlugins map required by a profile.

    Existing entries remain pinned even when a plugin temporarily disappears
    from the inventory. When it reappears, the current profile resumes control.
    """
    pinned = _parse_pinned_plugins(current_local)
    non_local = _effective_plugin_state(
        [record for record in records if record.scope is not PluginScope.LOCAL])
    local = _effective_plugin_state(
        [record for record in records if record.scope is PluginScope.LOCAL])
    everything = _effective_plugin_state(records)
    managed = {record.plugin_id for record in records
               if record.scope is PluginScope.MANAGED}
    allowed_set = _parse_allowed_plugins(allowed)

    # Start with every pin so uninstall/reinstall cycles cannot silently hand
    # a plugin back to its user/project baseline.
    result = dict(pinned)

    def carried(plugin_id):
        if plugin_id in local:
            return local[plugin_id]
        return pinned.get(plugin_id)

    for plugin_id in sorted(everything):
        if plugin_id in managed:
            keep = carried(plugin_id)
            if keep is None:
                result.pop(plugin_id, None)
            else:
                result[plugin_id] = keep
            continue
        if is_self_plugin(plugin_id) and plugin_id not in allowed_set:
            keep = carried(plugin_id)
            if keep is None:
                result.pop(plugin_id, None)
            else:
                result[plugin_id] = keep
            continue

        desired = plugin_id in allowed_set
        if plugin_id in pinned or plugin_id in local or plugin_id not in non_local:
            result[plugin_id] = desired
        elif desired != non_local[plugin_id]:
            result[plugin_id] = desired
        else:
            result.pop(plugin_id, None)

    return {str(plugin_id): result[plugin_id]
            for plugin_id in sorted(result, key=str)}


def summarize_plugin_changes(records, enabled_plugins):
    """Count genuine next-session changes produced by enabled_plugins."""
    parsed_enabled = _parse_pinned_plugins(enabled_plugins)
    current = _effective_plugin_state(records)
    managed = _effective_plugin_state(
        [record for record in records if record.scope is PluginScope.MANAGED])
    non_local = _effective_plugin_state(
        [record for record in records if record.scope is not PluginScope.LOCAL])
    disabled = enabled = 0
    for plugin_id, now in current.items():
        if plugin_id in managed:
            future = managed[plugin_id]
        elif plugin_id in parsed_enabled:
            future = parsed_enabled[plugin_id]
        else:
            future = non_local.get(plugin_id, now)
        if future and not now:
            enabled += 1
        elif now and not future:
            disabled += 1
    return disabled, enabled

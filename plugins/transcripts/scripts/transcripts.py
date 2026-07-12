#!/usr/bin/env python3
"""Configurable, worktree-safe Markdown transcripts for Claude Code and Codex."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

LEVELS = ("conversation", "activity", "full")
AGENTS = ("claude", "codex")
MAX_BLOCK_BYTES = 32 * 1024
CODEX_DATA_DIR = Path.home() / ".local" / "share" / "codex-transcripts"
CLAUDE_FALLBACK_DATA_DIR = Path.home() / ".local" / "share" / "claude-transcripts"
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)\b(\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_-]{12,})\b"),
    re.compile(r"\b(gh[oprsu]_[A-Za-z0-9]{20,})\b"),
    re.compile(r"(?i)\b(authorization\s*:\s*bearer\s+)([^\s]+)"),
]
INTERNAL_BLOCK_PATTERNS = [
    re.compile(r"<(permissions instructions|collaboration_mode|skills_instructions|apps_instructions|plugins_instructions)>.*?</\1>", re.I | re.S),
    re.compile(r"<encrypted_content>.*?</encrypted_content>", re.I | re.S),
]


@dataclass
class Entry:
    title: str
    body: str
    timestamp: str = ""
    sequence: int = 0


def run_git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def primary_root(cwd: Path) -> Path:
    common = run_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common and Path(common).name == ".git":
        return Path(common).parent
    top = run_git(cwd, "rev-parse", "--show-toplevel")
    return Path(top) if top else cwd


def git_metadata(cwd: Path) -> dict[str, str]:
    top = run_git(cwd, "rev-parse", "--show-toplevel") or str(cwd)
    branch = run_git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD")
    worktree = Path(top).name
    if not branch:
        branch = f"detached-{worktree or 'worktree'}"
    origin = re.sub(r"[^A-Za-z0-9._-]", "_", branch.replace("/", "__")) or "no-branch"
    return {"branch": branch, "origin": origin, "worktree": worktree, "worktree_root": top}


def common_git_dir(cwd: Path) -> Path | None:
    value = run_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(value) if value else None


def resolve_data_dir(agent: str, explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("TRANSCRIPTS_DATA_DIR")
    if env:
        return Path(env).expanduser()
    return CODEX_DATA_DIR if agent == "codex" else CLAUDE_FALLBACK_DATA_DIR


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".transcripts-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def global_config_path(agent: str, explicit_data_dir: str = "") -> Path:
    return resolve_data_dir(agent, explicit_data_dir) / "config.json"


def repo_config_path(cwd: Path, agent: str) -> Path | None:
    common = common_git_dir(cwd)
    return common / f"{agent}-transcripts" / "config.json" if common else None


def configured_level(path: Path | None) -> str | None:
    level = read_json(path).get("verbosity") if path else None
    return level if level in LEVELS else None


def effective_level(cwd: Path, agent: str, explicit_data_dir: str = "") -> tuple[str, str, str | None]:
    global_level = configured_level(global_config_path(agent, explicit_data_dir)) or "conversation"
    repo_level = configured_level(repo_config_path(cwd, agent))
    return repo_level or global_level, global_level, repo_level


def redact(value: str) -> str:
    for pattern in SECRET_PATTERNS:
        if pattern.groups == 3:
            value = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", value)
        elif pattern.groups == 2:
            value = pattern.sub(lambda m: f"{m.group(1)}[REDACTED]", value)
        else:
            value = pattern.sub("[REDACTED]", value)
    return value


def strip_internal(value: str) -> str:
    for pattern in INTERNAL_BLOCK_PATTERNS:
        value = pattern.sub("[internal content omitted]", value)
    lines = []
    for line in value.splitlines():
        if re.search(r'"role"\s*:\s*"(?:developer|system)"', line, re.I):
            lines.append("[internal message omitted]")
        elif re.search(r'encrypted_content|internal_chat_message_metadata_passthrough', line, re.I):
            lines.append("[internal metadata omitted]")
        else:
            lines.append(line)
    return "\n".join(lines)


def safe_block(value: str) -> str:
    cleaned = redact(strip_internal(value))
    raw = cleaned.encode("utf-8", errors="replace")
    if len(raw) > MAX_BLOCK_BYTES:
        cleaned = raw[:MAX_BLOCK_BYTES].decode("utf-8", errors="ignore")
        cleaned += f"\n\n[truncated: original content was {len(raw)} bytes]"
    return cleaned


def fenced(value: str) -> str:
    fence = "```"
    while fence in value:
        fence += "`"
    return f"{fence}text\n{value}\n{fence}"


def text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", "")) for item in content
            if isinstance(item, dict) and item.get("type") in {"output_text", "input_text", "text"} and item.get("text")
        )
    return ""


def parsed_arguments(payload: dict[str, Any]) -> Any:
    raw = payload.get("arguments", payload.get("input", ""))
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def summarize_codex_call(payload: dict[str, Any]) -> tuple[str, str]:
    kind = str(payload.get("type", "tool"))
    name = str(payload.get("name") or kind.replace("_call", ""))
    args = parsed_arguments(payload)
    command = ""
    if isinstance(args, dict):
        command = str(args.get("cmd") or args.get("command") or args.get("query") or "")
    elif isinstance(args, str):
        command = args
    if name in {"exec", "exec_command", "shell_command"}:
        nested = re.search(r'(?:cmd|command)\s*:\s*["\'](.{1,500}?)["\']\s*(?:,|})', command, re.S)
        if nested:
            command = nested.group(1).replace("\\n", "\n").replace("\\\"", '"')
        summary = "Ran " + (command.strip() or name)
    elif kind == "web_search_call":
        summary = "Searched the web" + (f" for {command.strip()}" if command else "")
    elif name == "apply_patch" or "patch" in name:
        summary = "Applied a patch"
    else:
        summary = f"Called {name}" + (f" with {command.strip()}" if command else "")
    detail = json.dumps(args, indent=2, ensure_ascii=False) if not isinstance(args, str) else args
    return summary, detail


def summarize_claude_tool(name: str, tool_input: Any) -> tuple[str, str]:
    detail = json.dumps(tool_input, indent=2, ensure_ascii=False) if not isinstance(tool_input, str) else tool_input
    values = tool_input if isinstance(tool_input, dict) else {}
    if name == "Bash":
        summary = "Ran " + str(values.get("command") or "Bash")
    elif name in {"Read", "Write", "Edit", "NotebookEdit"}:
        path = values.get("file_path") or values.get("notebook_path") or ""
        verb = {"Read": "Read", "Write": "Wrote", "Edit": "Edited", "NotebookEdit": "Edited notebook"}[name]
        summary = f"{verb} {path}".rstrip()
    elif name in {"WebSearch", "WebFetch"}:
        target = values.get("query") or values.get("url") or ""
        summary = ("Searched the web" if name == "WebSearch" else "Fetched") + (f" for {target}" if target else "")
    else:
        summary = f"Called {name}"
    return summary, detail


def parse_codex_entries(records: Iterable[dict[str, Any]], level: str) -> list[Entry]:
    entries: list[Entry] = []
    calls: dict[str, tuple[str, str]] = {}
    seen: set[tuple[str, str, str]] = set()
    seq = 0
    for record in records:
        seq += 1
        timestamp = str(record.get("timestamp") or "")
        record_type = record.get("type")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_type = payload.get("type")
        if record_type == "event_msg" and payload_type in {"user_message", "agent_message"}:
            role = "User" if payload_type == "user_message" else "Assistant"
            body = str(payload.get("message") or "")
            key = (role, str(payload.get("phase") or ""), body)
            if body and key not in seen:
                entries.append(Entry(role, body, timestamp, seq)); seen.add(key)
            continue
        if record_type == "response_item" and payload_type == "message" and payload.get("role") in {"user", "assistant"}:
            role = "User" if payload["role"] == "user" else "Assistant"
            body = text_content(payload.get("content"))
            key = (role, str(payload.get("phase") or ""), body)
            if body and key not in seen:
                entries.append(Entry(role, body, timestamp, seq)); seen.add(key)
            continue
        if level == "conversation" or record_type != "response_item":
            continue
        if payload_type in {"function_call", "custom_tool_call", "web_search_call", "tool_search_call"}:
            call_id = str(payload.get("call_id") or payload.get("id") or "")
            summary, detail = summarize_codex_call(payload)
            calls[call_id] = (summary, detail)
            args = parsed_arguments(payload)
            elevated = isinstance(args, dict) and args.get("sandbox_permissions") == "require_escalated"
            elevated = elevated or "require_escalated" in detail
            body = safe_block(("Requested elevated execution; " if elevated else "") + summary)
            if level == "full" and detail:
                body += "\n\n" + fenced(safe_block(detail))
            entries.append(Entry("Activity", body, timestamp, seq))
        elif level == "full" and payload_type in {"function_call_output", "custom_tool_call_output", "tool_search_output"}:
            call_id = str(payload.get("call_id") or "")
            output = text_content(payload.get("output"))
            if not output and payload.get("output") is not None:
                output = json.dumps(payload.get("output"), indent=2, ensure_ascii=False)
            if output:
                summary = calls.get(call_id, ("Tool call", ""))[0]
                entries.append(Entry("Tool Output", summary + "\n\n" + fenced(safe_block(output)), timestamp, seq))
    return entries


def tool_fingerprint(name: str, tool_input: Any) -> str:
    raw = json.dumps([name, tool_input], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def permission_events(data: Path, session_id: str) -> list[dict[str, Any]]:
    path = data / "events" / f"{session_id}.jsonl"
    return read_jsonl(path) if path.is_file() else []


def parse_claude_entries(records: Iterable[dict[str, Any]], level: str, permissions: list[dict[str, Any]]) -> list[Entry]:
    entries: list[Entry] = []
    seq = 0
    executed: set[str] = set()
    tool_results: set[str] = set()
    records = list(records)
    for record in records:
        if record.get("type") == "user" and isinstance(record.get("message"), dict):
            content = record["message"].get("content")
            if isinstance(content, list):
                tool_results.update(str(item.get("tool_use_id")) for item in content if isinstance(item, dict) and item.get("type") == "tool_result")
    for record in records:
        seq += 1
        timestamp = str(record.get("timestamp") or "")
        if record.get("type") not in {"user", "assistant"} or not isinstance(record.get("message"), dict):
            continue
        role = record["message"].get("role")
        content = record["message"].get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}] if isinstance(content, str) else []
        for block_index, block in enumerate(blocks):
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text" and block.get("text"):
                entries.append(Entry("User" if role == "user" else "Assistant", str(block["text"]), timestamp, seq * 100 + block_index))
            elif role == "assistant" and kind == "tool_use" and level != "conversation":
                name = str(block.get("name") or "tool")
                tool_input = block.get("input") or {}
                summary, detail = summarize_claude_tool(name, tool_input)
                fingerprint = tool_fingerprint(name, tool_input)
                if str(block.get("id") or "") in tool_results:
                    executed.add(fingerprint)
                body = safe_block(summary)
                if level == "full" and detail:
                    body += "\n\n" + fenced(safe_block(detail))
                entries.append(Entry("Activity", body, timestamp, seq * 100 + block_index))
            elif role == "user" and kind == "tool_result" and level == "full":
                result = text_content(block.get("content"))
                if not result and block.get("content") is not None:
                    result = json.dumps(block.get("content"), indent=2, ensure_ascii=False)
                if result:
                    entries.append(Entry("Tool Output", fenced(safe_block(result)), timestamp, seq * 100 + block_index))
    if level != "conversation":
        for index, event in enumerate(permissions):
            event_name = str(event.get("event") or "PermissionRequest")
            summary = str(event.get("summary") or event.get("tool_name") or "tool")
            fingerprint = str(event.get("fingerprint") or "")
            if event_name == "PermissionDenied":
                body = f"Permission denied: {summary}"
            elif fingerprint and fingerprint in executed:
                body = f"Permission requested; tool executed: {summary}"
            else:
                body = f"Permission requested: {summary}"
            entries.append(Entry("Permission", safe_block(body), str(event.get("timestamp") or ""), 50_000_000 + index))
    return sorted(entries, key=lambda entry: (entry.timestamp, entry.sequence))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open(errors="replace") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    records.append(value)
    except OSError:
        pass
    return records


def timestamp_slug(value: str) -> str:
    match = re.match(r"(\d{4}-\d\d-\d\d)T(\d\d):(\d\d):(\d\d)", value)
    return f"{match.group(1)}_{match.group(2)}-{match.group(3)}-{match.group(4)}" if match else dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def find_archive(root: Path, session_id: str) -> Path | None:
    return next(root.glob(f"**/*_{session_id}.md"), None) if root.exists() else None


def ensure_excludes(cwd: Path) -> None:
    common = common_git_dir(cwd)
    if not common:
        return
    path = common / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.exists() else ""
    lines = existing.splitlines()
    additions = [item for item in ("/.claude/sessions/", "/.codex/sessions/") if item not in lines]
    if additions:
        with path.open("a") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write("\n".join(additions) + "\n")


def transcript_metadata(agent: str, records: list[dict[str, Any]]) -> tuple[str, str]:
    if agent == "codex":
        meta = next((r.get("payload") for r in records if r.get("type") == "session_meta" and isinstance(r.get("payload"), dict)), {})
        started = str(meta.get("timestamp") or (records[0].get("timestamp") if records else "") or "unknown")
        return started, str(meta.get("model") or "")
    started = str(next((r.get("timestamp") for r in records if r.get("timestamp")), "unknown"))
    model = ""
    for record in records:
        message = record.get("message")
        if isinstance(message, dict) and message.get("model"):
            model = str(message["model"]); break
    return started, model


def write_markdown(source: Path, cwd: Path, session_id: str, agent: str, explicit_data_dir: str = "", model: str = "") -> Path:
    records = read_jsonl(source)
    if not session_id:
        session_id = source.stem
    if not session_id:
        raise ValueError("session ID is unavailable")
    started, detected_model = transcript_metadata(agent, records)
    root = primary_root(cwd)
    git = git_metadata(cwd)
    archives = root / f".{agent}" / "sessions"
    output = find_archive(archives, session_id) or archives / git["origin"] / f"{timestamp_slug(started)}_{session_id}.md"
    level, _, _ = effective_level(cwd, agent, explicit_data_dir)
    if agent == "claude":
        events = permission_events(resolve_data_dir(agent, explicit_data_dir), session_id)
        entries = parse_claude_entries(records, level, events)
        title = "Claude Code"
    else:
        entries = parse_codex_entries(records, level)
        title = "Codex"
    lines = [
        f"# {title} Session Transcript",
        f"- **Started:** {started}", f"- **Branch:** {git['branch']}", f"- **Origin:** {git['origin']}",
        f"- **Worktree:** {git['worktree']}", f"- **Worktree Root:** {git['worktree_root']}",
        f"- **Working Dir:** {cwd}",
    ]
    actual_model = model or detected_model
    if actual_model:
        lines.append(f"- **Model:** {actual_model}")
    lines.extend([f"- **Verbosity:** {level}", f"- **Session ID:** {session_id}", "", "---", ""])
    for entry in entries:
        lines.extend([f"## {entry.title}", "", entry.body, ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".session-archive-", dir=output.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write("\n".join(lines).rstrip() + "\n")
        os.replace(name, output)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
    ensure_excludes(cwd)
    return output


def command_export(args: argparse.Namespace) -> int:
    try:
        hook = json.load(sys.stdin)
        source = Path(str(hook.get("transcript_path") or ""))
        cwd = Path(str(hook.get("cwd") or Path.cwd()))
        if not source.is_file():
            raise ValueError(f"transcript is unavailable: {source}")
        write_markdown(source, cwd, str(hook.get("session_id") or ""), args.agent, args.data_dir, str(hook.get("model") or ""))
    except Exception as exc:
        print(f"transcripts: {exc}", file=sys.stderr)
    return 0


def command_capture_permission(args: argparse.Namespace) -> int:
    try:
        hook = json.load(sys.stdin)
        session_id = str(hook.get("session_id") or "")
        if not session_id:
            return 0
        name = str(hook.get("tool_name") or "tool")
        tool_input = hook.get("tool_input") or {}
        summary, _ = summarize_claude_tool(name, tool_input)
        event = {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": str(hook.get("hook_event_name") or args.event),
            "tool_name": name,
            "summary": safe_block(summary),
            "fingerprint": tool_fingerprint(name, tool_input),
        }
        path = resolve_data_dir("claude", args.data_dir) / "events" / f"{session_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception as exc:
        print(f"transcripts: {exc}", file=sys.stderr)
    return 0


def command_status(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    effective, global_level, repo_level = effective_level(cwd, args.agent, args.data_dir)
    print(f"agent: {args.agent}")
    print(f"effective: {effective}")
    print(f"global: {global_level}")
    print(f"repository: {repo_level or 'not set'}")
    print(f"archive: {primary_root(cwd) / f'.{args.agent}' / 'sessions'}")
    return 0


def command_verbosity(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    if args.repo:
        path = repo_config_path(cwd, args.agent)
        if path is None:
            print("transcripts: --repo requires a Git repository", file=sys.stderr); return 2
        scope = "repository"
    else:
        path = global_config_path(args.agent, args.data_dir); scope = "global"
    if args.level == "reset":
        if not args.repo:
            print("transcripts: only repository overrides can be reset", file=sys.stderr); return 2
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        print("repository transcript verbosity reset"); return 0
    atomic_json(path, {"verbosity": args.level})
    print(f"{scope} {args.agent} transcript verbosity set to {args.level}")
    return 0


def session_id_from_archive(path: Path) -> str:
    match = re.search(r"^- \*\*Session ID:\*\* (.+)$", path.read_text(errors="replace"), re.M)
    return match.group(1).strip() if match else ""


def raw_sessions_by_id(agent: str) -> dict[str, Path]:
    root = Path.home() / f".{agent}" / ("projects" if agent == "claude" else "sessions")
    result: dict[str, Path] = {}
    if root.exists():
        for path in root.glob("**/*.jsonl"):
            result[path.stem if agent == "claude" else path.name.rsplit("-", 5)[-1].removesuffix(".jsonl")] = path
            match = re.search(r"([0-9a-f]{8}-[0-9a-f-]{27})\.jsonl$", path.name)
            if match:
                result[match.group(1)] = path
    return result


def command_rebuild(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve()
    root = primary_root(cwd) / f".{args.agent}" / "sessions"
    archives = list(root.glob("**/*.md")) if root.exists() else []
    if args.current:
        pool = [p for p in archives if f"- **Working Dir:** {cwd}" in p.read_text(errors="replace")] or archives
        archives = [max(pool, key=lambda p: p.stat().st_mtime)] if pool else []
    raw = raw_sessions_by_id(args.agent)
    rebuilt = missing = failed = 0
    for archive in archives:
        session_id = session_id_from_archive(archive)
        source = raw.get(session_id)
        if not source:
            missing += 1; continue
        try:
            write_markdown(source, cwd, session_id, args.agent, args.data_dir); rebuilt += 1
        except Exception as exc:
            failed += 1; print(f"transcripts: failed {session_id}: {exc}", file=sys.stderr)
    print(f"rebuilt: {rebuilt}; missing source: {missing}; failed: {failed}")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="transcripts")
    parser.add_argument("--agent", choices=AGENTS, default="codex")
    parser.add_argument("--data-dir", default="")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export"); export.set_defaults(func=command_export)
    permission = sub.add_parser("capture-permission")
    permission.add_argument("--event", choices=("PermissionRequest", "PermissionDenied"), required=True)
    permission.set_defaults(func=command_capture_permission)
    status = sub.add_parser("status"); status.add_argument("--cwd", default=os.getcwd()); status.set_defaults(func=command_status)
    verbosity = sub.add_parser("verbosity"); verbosity.add_argument("level", choices=(*LEVELS, "reset"))
    scope = verbosity.add_mutually_exclusive_group(required=True)
    scope.add_argument("--global", dest="global_scope", action="store_true"); scope.add_argument("--repo", action="store_true")
    verbosity.add_argument("--cwd", default=os.getcwd()); verbosity.set_defaults(func=command_verbosity)
    rebuild = sub.add_parser("rebuild"); mode = rebuild.add_mutually_exclusive_group(required=True)
    mode.add_argument("--current", action="store_true"); mode.add_argument("--all", action="store_true")
    rebuild.add_argument("--cwd", default=os.getcwd()); rebuild.set_defaults(func=command_rebuild)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

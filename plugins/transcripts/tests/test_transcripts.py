#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "transcripts.py"
SPEC = importlib.util.spec_from_file_location("transcripts", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def codex(kind, payload):
    return {"timestamp": "2026-07-10T12:00:00Z", "type": kind, "payload": payload}


def claude(kind, content, timestamp="2026-07-10T12:00:00Z"):
    return {"timestamp": timestamp, "type": kind, "message": {"role": kind, "content": content}}


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.codex_records = [
            codex("event_msg", {"type": "user_message", "message": "fix it"}),
            codex("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "fix it"}]}),
            codex("event_msg", {"type": "agent_message", "phase": "commentary", "message": "Checking."}),
            codex("response_item", {"type": "function_call", "name": "exec_command", "call_id": "1", "arguments": json.dumps({"cmd": "echo ok", "sandbox_permissions": "require_escalated"})}),
            codex("response_item", {"type": "function_call_output", "call_id": "1", "output": "TOKEN=sk-proj-abcdefghijklmnop\nok"}),
            codex("response_item", {"type": "message", "role": "developer", "content": [{"type": "input_text", "text": "hidden policy"}]}),
            codex("response_item", {"type": "reasoning", "summary": "hidden reasoning"}),
            codex("response_item", {"type": "message", "role": "assistant", "phase": "final_answer", "content": [{"type": "output_text", "text": "Done."}]}),
        ]
        self.claude_records = [
            claude("user", "fix it"),
            claude("assistant", [{"type": "thinking", "thinking": "hidden reasoning"}, {"type": "text", "text": "Checking."}, {"type": "tool_use", "id": "tool-1", "name": "Bash", "input": {"command": "echo ok"}}], "2026-07-10T12:00:01Z"),
            claude("user", [{"type": "tool_result", "tool_use_id": "tool-1", "content": "sk-proj-abcdefghijklmnop\nok"}], "2026-07-10T12:00:02Z"),
            claude("assistant", [{"type": "text", "text": "Done."}], "2026-07-10T12:00:03Z"),
        ]

    @staticmethod
    def rendered(entries):
        return "\n".join(entry.body for entry in entries)

    def test_codex_levels(self):
        conversation = self.rendered(MODULE.parse_codex_entries(self.codex_records, "conversation"))
        activity = self.rendered(MODULE.parse_codex_entries(self.codex_records, "activity"))
        full = self.rendered(MODULE.parse_codex_entries(self.codex_records, "full"))
        self.assertEqual(conversation.count("fix it"), 1)
        self.assertNotIn("echo ok", conversation)
        self.assertIn("Requested elevated execution; Ran echo ok", activity)
        self.assertNotIn("TOKEN", activity)
        self.assertIn("[REDACTED]", full)
        self.assertNotIn("hidden", conversation)

    def test_claude_levels_and_permission_correlation(self):
        fingerprint = MODULE.tool_fingerprint("Bash", {"command": "echo ok"})
        permissions = [{"timestamp": "2026-07-10T12:00:00.5Z", "event": "PermissionRequest", "summary": "Ran echo ok", "fingerprint": fingerprint}]
        conversation = self.rendered(MODULE.parse_claude_entries(self.claude_records, "conversation", permissions))
        activity = self.rendered(MODULE.parse_claude_entries(self.claude_records, "activity", permissions))
        full = self.rendered(MODULE.parse_claude_entries(self.claude_records, "full", permissions))
        self.assertIn("fix it", conversation)
        self.assertIn("Done.", conversation)
        self.assertNotIn("echo ok", conversation)
        self.assertIn("Permission requested; tool executed: Ran echo ok", activity)
        self.assertNotIn("sk-proj", activity)
        self.assertIn("[REDACTED]", full)
        self.assertNotIn("hidden reasoning", full)

    def test_permission_denied(self):
        permissions = [{"event": "PermissionDenied", "summary": "Ran rm file", "timestamp": "2026-07-10T12:00:00Z"}]
        text = self.rendered(MODULE.parse_claude_entries([], "activity", permissions))
        self.assertIn("Permission denied: Ran rm file", text)

    def test_internal_content_and_truncation(self):
        value = '<permissions instructions>do not expose</permissions instructions>\n{"role":"developer","content":"hidden"}'
        cleaned = MODULE.safe_block(value)
        self.assertNotIn("do not expose", cleaned)
        self.assertNotIn('"content":"hidden"', cleaned)
        self.assertIn("omitted", cleaned)
        self.assertIn("[truncated:", MODULE.safe_block("x" * (MODULE.MAX_BLOCK_BYTES + 50)))

    def test_independent_global_config(self):
        with tempfile.TemporaryDirectory() as temp:
            MODULE.atomic_json(MODULE.global_config_path("claude", temp + "/claude"), {"verbosity": "activity"})
            MODULE.atomic_json(MODULE.global_config_path("codex", temp + "/codex"), {"verbosity": "full"})
            self.assertEqual(MODULE.effective_level(Path(temp), "claude", temp + "/claude")[0], "activity")
            self.assertEqual(MODULE.effective_level(Path(temp), "codex", temp + "/codex")[0], "full")

    def test_linked_worktree_archives_survive_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            main = Path(temp) / "main"
            linked = Path(temp) / "linked"
            main.mkdir()
            subprocess.run(["git", "-C", str(main), "init", "-q", "-b", "main"], check=True)
            subprocess.run(["git", "-C", str(main), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(main), "config", "user.email", "test@example.invalid"], check=True)
            (main / "file").write_text("x\n")
            subprocess.run(["git", "-C", str(main), "add", "file"], check=True)
            subprocess.run(["git", "-C", str(main), "commit", "-qm", "init"], check=True)
            subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", "-b", "feature/topic", str(linked)], check=True)
            source = Path(temp) / "claude.jsonl"
            source.write_text("\n".join(json.dumps(item) for item in self.claude_records) + "\n")
            output = MODULE.write_markdown(source, linked, "11111111-1111-4111-8111-111111111111", "claude", temp + "/data")
            self.assertTrue(str(output.resolve()).startswith(str(main.resolve())))
            self.assertIn("feature__topic", str(output))
            subprocess.run(["git", "-C", str(main), "worktree", "remove", str(linked)], check=True)
            subprocess.run(["git", "-C", str(main), "branch", "-D", "feature/topic"], check=True, stdout=subprocess.DEVNULL)
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()

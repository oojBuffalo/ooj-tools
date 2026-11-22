import json
from pathlib import Path
import runpy
import stat
import tempfile
import unittest
from unittest.mock import patch


TOOL = runpy.run_path(str(Path(__file__).with_name("herdr-recovery")))
CLAUDE = {"agent": "claude", "kind": "id", "source": "herdr:claude", "value": "claude-one"}
CODEX = {"agent": "codex", "kind": "id", "source": "herdr:codex", "value": "codex-one"}


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.panes = {"17": {"agent_session": CLAUDE}, "22": {"agent_session": CODEX}}
        self.layout = {
            "version": 3,
            "workspaces": [{
                "id": "wK",
                "public_pane_numbers": {"17": 52, "22": 55},
                "tabs": [{"panes": self.panes}],
            }],
        }

    def test_status_matches_sessions_to_each_pane(self):
        live = [
            {"pane_id": "wK:p1M", "agent": "claude", "agent_session": CLAUDE},
            {"pane_id": "wK:p1Q", "agent": "codex", "agent_session": CODEX},
        ]

        def herdr(*args):
            self.assertEqual(args, ("--session", "work", "api", "snapshot"))
            return json.dumps({"result": {"snapshot": {"panes": live}}})

        status = TOOL["status"]
        with patch.dict(status.__globals__, {"herdr": herdr}), patch("builtins.print"):
            self.assertTrue(status(self.layout, {"running": True}, ["--session", "work"]))
            live[1]["agent_session"] = {**CODEX, "value": "codex-two"}
            self.assertFalse(status(self.layout, {"running": True}, ["--session", "work"]))

    def test_status_flags_duplicate_saved_ids_while_offline(self):
        self.panes["22"]["agent_session"] = CLAUDE
        with patch("builtins.print"):
            self.assertFalse(TOOL["status"](self.layout, {"running": False}, []))

    def test_checkpoint_copies_bytes_and_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            config.write_bytes(b"# preserve comments\n[session]\nresume_agents_on_restore = false\n")
            self.assertFalse(TOOL["restore_setting"](config))
            directory = Path(tmp) / "checkpoint"
            data = json.dumps(self.layout).encode()
            with patch("builtins.print"):
                TOOL["checkpoint"](directory, data, config)
                with self.assertRaises(FileExistsError):
                    TOOL["checkpoint"](directory, b"new data", config)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual((directory / "session.json").read_bytes(), data)
            self.assertEqual((directory / "config.toml").read_bytes(), config.read_bytes())


if __name__ == "__main__":
    unittest.main()

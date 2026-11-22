# Herdr TUI recovery

Requires Herdr TUI 0.9.5 and Python 3.11 or later. Run these commands on the
host running the Herdr server.

```sh
./tools/herdr-recovery/herdr-recovery install
./tools/herdr-recovery/herdr-recovery status
```

`install` installs or updates Herdr's official Claude Code and Codex hooks.
In Codex, open `/hooks` and trust the Herdr hook. For any agent that was
already running when you installed, reopen the same conversation in its
pane to register its ID. Each hook reports the session ID to Herdr when an
agent starts or switches conversations. If you explicitly disabled restore
in `config.toml`, set `[session]` `resume_agents_on_restore = true`.
[Herdr integrations](https://herdr.dev/tui/docs/integrations/)

`status` compares the live Claude Code and Codex panes against the last
on-disk snapshot. Run it again after a few seconds if you just changed your
layout or switched conversations. It reports panes missing their current
session ID, duplicate saved IDs, and Herdr restore errors. Use
`--session NAME` before the command to select a named session.

After a crash or reboot, open Herdr as usual with `herdr` or
`herdr --session NAME`. Herdr restores the saved workspaces, tabs, splits,
and working directories. It starts `claude --resume <id>` or
`codex resume <id>` in each eligible pane using that pane's saved ID.
Other panes open as shells. Conversation history comes from the agent's own
session store and is limited to what the agent saved before the interruption.
[Herdr session state and restore](https://herdr.dev/tui/docs/session-state/)

To copy the latest saved layout and Herdr configuration to a new directory:

```sh
./tools/herdr-recovery/herdr-recovery checkpoint ~/herdr-checkpoint
```

The checkpoint contains private session metadata. To recover a checkpoint
while the affected Herdr server is stopped, save a copy of its current
`session.json`, copy in the checkpoint's `session.json`, and reopen the
session. Find the session directory with `herdr session list --json`.
The checkpoint's `config.toml` is available if you also need to recover
configuration. For recovery after disk loss, keep a copy of the checkpoint
and the agents' own session stores on another disk.

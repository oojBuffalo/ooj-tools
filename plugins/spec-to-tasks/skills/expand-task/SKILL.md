---
name: expand-task
description: This skill should be used when the user asks to "expand task N", "break task N into subtasks", "expand the complex tasks", "add subtasks to <task>", or otherwise wants a top-level task decomposed into concrete, sequenced subtasks. Writes a Subtasks section into the target task file.
---

# expand-task

Break one (or several) top-level tasks into specific, actionable subtasks.

Read `${CLAUDE_PLUGIN_ROOT}/references/task-format.md` (for the `## Subtasks` layout and `N.M` id
convention) and `${CLAUDE_PLUGIN_ROOT}/references/generation-guidelines.md` (for what a good,
atomic, testable unit looks like) before generating.

## Workflow

1. **Identify the target.** Resolve the task id(s) the user named to files under the task directory
   (default `tasks/`). If the user says "expand the complex tasks" / "expand all", read
   `complexity-report.md` (or the `complexity` frontmatter) and expand every task at or above the
   threshold, highest first.

2. **Read the task file fully**, including any `## Complexity Analysis` section.

3. **Choose the guidance source:**
   - If the task has a **Suggested expansion approach** (from `analyze-complexity`), follow it, and
     use `recommended_subtasks` as the target count.
   - Otherwise generate a sensible breakdown from the task's own description and details.
   - If the user asked for *research* mode, look up current best practices for the task's domain
     first. If working in an existing repo (*codebase-aware*), explore with Glob/Grep/Read so the
     subtasks integrate with real code.

4. **Determine the subtask count.** Honor an explicit number from the user; else use
   `recommended_subtasks`; else pick an appropriate number. Never expand a task the analysis marked
   `recommended_subtasks: 0` unless the user insists.

5. **Generate subtasks.** Each needs a clear actionable title, a description, implementation details,
   a short test approach, and dependencies on sibling subtasks where a real ordering exists. Number
   them `N.1, N.2, …` where `N` is the parent id — sequentially from 1, never reusing the parent id
   scheme incorrectly.

6. **Write the `## Subtasks` section** into the parent task file using the exact format from
   `task-format.md`:
   ```markdown
   ## Subtasks
   ### N.1 <title> — status: pending
   <description> **Details:** … **Test:** … **Depends on:** —
   ```
   If a `## Subtasks` section already exists, replace it (unless the user asks to append).

7. **Rebuild the overview** so subtask counts update, and validate the tree:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" overview  --tasks-dir <tasks-dir>
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" validate --tasks-dir <tasks-dir>
   ```

8. **Report** which task(s) were expanded and how many subtasks each gained.

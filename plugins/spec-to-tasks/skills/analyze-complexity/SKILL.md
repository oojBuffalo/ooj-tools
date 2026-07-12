---
name: analyze-complexity
description: This skill should be used when the user asks to "analyze task complexity", "which tasks should I break down", "score the tasks", "generate a complexity report", or otherwise wants to know how hard each task in the tasks/ tree is and how many subtasks it warrants. Annotates each task file and writes a complexity report.
---

# analyze-complexity

Score every task in the task tree for implementation complexity and recommend how far to break it
down. This prepares the tree for the `expand-task` skill.

Read `${CLAUDE_PLUGIN_ROOT}/references/task-format.md` first — it defines the frontmatter fields and
the `## Complexity Analysis` section this skill writes.

## Workflow

1. **Find the task directory** (default `tasks/`) and read every task file in it. Skip the generated
   `overview.md` and `complexity-report.md`.

2. **Set the threshold.** Default is **5** (tasks scoring ≥ 5 are flagged as worth expanding). Honor
   a different threshold if the user gives one.

3. **Optional modes (only when asked).**
   - *Codebase-aware*: explore the repo with Glob/Grep/Read and score against the *actual* code that
     must change — existing abstractions lower complexity, greenfield/refactor work raises it.
   - *Research*: factor in current best practices and known pitfalls for each task's domain.

4. **Score each task.** Assign:
   - `complexity` — an integer 1–10 reflecting implementation effort, technical risk, dependencies,
     and testing burden.
   - `recommended_subtasks` — how many subtasks it should break into (`0` if it is already atomic).
   - A short **reasoning** for the score.
   - A **suggested expansion approach** — one or two sentences describing how to split the task, in
     enough detail that `expand-task` can follow it.

5. **Write results back into each task file:**
   - Set the `complexity` and `recommended_subtasks` frontmatter fields.
   - Append (or replace) a `## Complexity Analysis` section containing the reasoning, ending with a
     line: `**Suggested expansion approach:** …`.

6. **Write the report.** Regenerate `<tasks-dir>/complexity-report.md` — a table sorted by
   descending complexity with columns: ID, Title, Complexity, Recommended subtasks, and an
   "Expand?" flag (yes when `complexity` ≥ threshold). Include the threshold used and a one-line
   summary of how many tasks are flagged.

7. **Rebuild the overview** so the new complexity values show up:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" overview --tasks-dir <tasks-dir>
   ```

8. **Report** which tasks are flagged for expansion and suggest running `expand-task` on the
   highest-complexity ones first.

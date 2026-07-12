---
name: parse-spec
description: This skill should be used when the user asks to "parse this PRD", "break down this spec into tasks", "turn this MVP/requirements doc into tasks", "generate tasks from <file>", or otherwise convert a product/requirements/spec document into a structured task list. Produces a readable markdown task tree under tasks/.
---

# parse-spec

Convert a PRD, spec, or MVP document into an ordered, dependency-aware set of markdown task files.

Read these first, then follow them exactly:
- `${CLAUDE_PLUGIN_ROOT}/references/task-format.md` — the on-disk task-file schema.
- `${CLAUDE_PLUGIN_ROOT}/references/generation-guidelines.md` — how to shape good tasks.

## Workflow

1. **Locate the spec.** Use the file path the user gives. If none is given, ask for it (or, if the
   conversation clearly contains the spec text, use that). Read the whole document before generating.

2. **Pick the task directory.** Default to `tasks/` at the project root. Honor an explicit location
   if the user names one, and reuse it for every later command.

3. **Determine the starting id.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" next-id --tasks-dir <tasks-dir>
   ```
   Number new tasks sequentially from that value (usually 1 for a fresh project).

4. **Decide how many tasks.** If the user states a count, produce exactly that many. Otherwise pick
   a number that fits the spec's scope per the generation guidelines (a typical PRD → ~10–15).

5. **Optional modes (only when asked).**
   - *Codebase-aware*: when working in an existing repo, first explore with Glob/Grep/Read and make
     tasks build on the current code.
   - *Research*: when asked, look up current best practices/library versions and fold specifics into
     each task's Details.

6. **Generate the tasks.** For each task derive a clear title, a one–two sentence description,
   concrete implementation details, a test strategy, a priority, and dependencies. Follow every rule
   in the generation guidelines: atomic scope, foundation-first ordering, dependencies pointing only
   to lower ids, strict fidelity to explicit tech choices in the spec, most-direct implementation.

7. **Write one file per task** at `<tasks-dir>/<NNN>-<slug>.md` using the exact frontmatter and
   section layout from `task-format.md`. Leave `complexity` and `recommended_subtasks` blank — the
   `analyze-complexity` skill fills them.

8. **Rebuild the index and validate:**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" overview  --tasks-dir <tasks-dir>
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tasks.py" validate --tasks-dir <tasks-dir>
   ```
   If `validate` reports errors (missing dependency, forward dependency, or a cycle), fix the
   offending task files and rerun until it passes.

9. **Report** the count of tasks written and point the user at `<tasks-dir>/overview.md`. Suggest
   running `analyze-complexity` next to find which tasks need expanding.

# Task-file format

The shared on-disk format for every skill in this plugin. There is **no JSON source of truth** —
each task is one human-readable markdown file, and two generated index files summarize them.

## Location

- One file per top-level task: `tasks/<NNN>-<slug>.md`
  - `<NNN>` is the zero-padded task id (`001`, `002`, …); `<slug>` is a short kebab-case title.
  - Example: `tasks/002-user-authentication.md`.
- Generated (never hand-authored — rebuilt by `scripts/tasks.py`):
  - `tasks/overview.md` — dashboard table of all tasks.
  - `tasks/complexity-report.md` — written by the `analyze-complexity` skill.

Default parent directory is `tasks/` at the project root. If the user names a different directory,
use that consistently and pass it to the helper script with `--tasks-dir`.

## Task file structure

```markdown
---
id: 2
title: User authentication
status: pending
priority: medium
dependencies: [1]
complexity:
recommended_subtasks:
---

## Description
One or two sentences on what this task delivers.

## Details
Implementation guidance: approach, key files, pseudo-code, libraries to use.

## Test Strategy
How to verify the task is correctly implemented.
```

### Frontmatter fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | Sequential, starts at 1, unique. Matches the `<NNN>` in the filename. |
| `title` | string | Concise; do **not** include the id in the title. |
| `status` | enum | `pending` \| `in-progress` \| `review` \| `done` \| `deferred` \| `cancelled`. New tasks are `pending`. |
| `priority` | enum | `high` \| `medium` \| `low`. Default `medium`. |
| `dependencies` | list[int] | Ids this task depends on. **Only lower ids** (a task may depend only on tasks defined before it). Empty list `[]` if none. |
| `complexity` | int 1–10 or blank | Filled by `analyze-complexity`; blank until then. |
| `recommended_subtasks` | int or blank | Filled by `analyze-complexity`; `0` means no expansion needed. |

### Optional sections (added by later skills)

- `## Complexity Analysis` — added by `analyze-complexity`. Holds the score reasoning and a
  **Suggested expansion approach:** line that `expand-task` consumes as guidance.
- `## Subtasks` — added by `expand-task`. Each subtask is a `###` heading with a `N.M` id:

  ```markdown
  ## Subtasks
  ### 2.1 Set up the auth database schema — status: pending
  Create the users/sessions tables. **Details:** … **Test:** … **Depends on:** —

  ### 2.2 Implement password hashing — status: pending
  … **Depends on:** 2.1
  ```

  Subtask ids are `<parentId>.<n>`, numbered sequentially from 1 within the parent. Subtask
  `Depends on:` references sibling subtask ids (or `—` for none).

## Rules the helper script enforces (`scripts/tasks.py validate`)

- Every id in a `dependencies` list must exist.
- A dependency id must be **strictly less** than the task's own id.
- The dependency graph must be acyclic.

Run `scripts/tasks.py overview` after any change to regenerate `tasks/overview.md`, and
`scripts/tasks.py validate` to confirm the graph is sound.

# Task generation guidelines

Principles for turning a spec into tasks, and tasks into subtasks. These apply to every skill in
the plugin. (Workflow inspired by `eyaltoledano/claude-task-master`; wording is original.)

## What a good task looks like

- **Atomic and single-purpose.** One task = one logical unit of work a developer could pick up and
  finish. If a task obviously splits into "do X, then Y, then Z", it is too big — either split it
  now or mark it for expansion.
- **Actionable.** The title is a concrete action ("Implement JWT session middleware"), not a theme
  ("Authentication"). Never put the id number in the title.
- **Self-contained detail.** The `## Details` section should carry enough implementation guidance —
  approach, key files, pseudo-code, specific libraries/APIs — that the task can be executed without
  re-reading the whole spec.
- **Always testable.** Every task and subtask needs a `## Test Strategy` describing how to confirm
  it works. Subtasks may set this to a short line.

## Ordering and dependencies

- **Foundation first.** Order tasks so setup, scaffolding, data models, and core plumbing come
  before the features that build on them; advanced/polish work comes last.
- **Depend only backward.** A task may only list dependencies with a **lower id** than its own.
  Assign ids in implementation order so this holds naturally.
- **Minimal dependencies.** Add a dependency only when the task genuinely cannot start until the
  other is done. Do not chain everything to task 1 out of habit.

## Fidelity to the spec

- **Honor explicit choices.** If the spec names specific frameworks, libraries, database schemas,
  versions, or architectural constraints, adopt them exactly. Do not substitute alternatives or
  drop stated requirements.
- **Fill the gaps, don't invent scope.** Where the spec is silent on *how*, choose the most direct,
  conventional implementation. Where it is silent on *what*, do not add features it never asked for.
- **Most direct path.** Prefer the simplest implementation that satisfies the requirement. Avoid
  over-engineering, speculative abstraction, and gold-plating.

## How many tasks / subtasks

- If the user gives an explicit count, produce exactly that many.
- Otherwise choose a number that fits the spec's scope and complexity — richer, more detailed specs
  warrant more tasks. A typical PRD lands around 10–15 top-level tasks, but do not pad or truncate
  to hit a number.
- For subtasks, honor the parent's `recommended_subtasks` when set by `analyze-complexity`.

## Optional modes (only when the user asks)

- **Codebase-aware.** When working inside an existing repo, first explore with Glob/Grep/Read to
  learn the stack, conventions, and what already exists. Generate tasks that build on the current
  code rather than duplicating it, and reference real files/patterns in `## Details`.
- **Research.** When asked to research, look up current best practices, library versions, and
  common pitfalls before generating, and fold specific, current recommendations into `## Details`.

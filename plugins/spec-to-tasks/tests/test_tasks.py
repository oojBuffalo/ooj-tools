"""Unit tests for scripts/tasks.py (the markdown task-store helper)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tasks as tm  # noqa: E402


def write_task(
    tasks_dir: Path,
    task_id: int,
    *,
    title: str = "A task",
    status: str = "pending",
    priority: str = "medium",
    dependencies: str = "[]",
    complexity: str = "",
    recommended_subtasks: str = "",
    body: str = "\n## Description\nDo the thing.\n",
) -> Path:
    """Write a minimal task file and return its path."""
    path = tasks_dir / f"{task_id:03d}-task.md"
    path.write_text(
        "---\n"
        f"id: {task_id}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        f"dependencies: {dependencies}\n"
        f"complexity: {complexity}\n"
        f"recommended_subtasks: {recommended_subtasks}\n"
        "---\n" + body,
        encoding="utf-8",
    )
    return path


def test_split_frontmatter_roundtrip():
    fm, body = tm.split_frontmatter("---\nid: 1\ntitle: Hi\n---\n## Description\nx\n")
    assert fm["id"] == "1"
    assert fm["title"] == "Hi"
    assert "## Description" in body


def test_split_frontmatter_absent():
    fm, body = tm.split_frontmatter("# no frontmatter\n")
    assert fm == {}
    assert body == "# no frontmatter\n"


def test_parse_deps_variants():
    assert tm._parse_deps("[]") == []
    assert tm._parse_deps("") == []
    assert tm._parse_deps("[1, 3]") == [1, 3]
    assert tm._parse_deps("1, 2, 3") == [1, 2, 3]


def test_next_id_empty(tmp_path, capsys):
    (tmp_path / "tasks").mkdir()
    assert tm.cmd_next_id(tmp_path / "tasks") == 0
    assert capsys.readouterr().out.strip() == "1"


def test_next_id_after_three(tmp_path, capsys):
    d = tmp_path / "tasks"
    d.mkdir()
    for i in (1, 2, 3):
        write_task(d, i)
    assert tm.cmd_next_id(d) == 0
    assert capsys.readouterr().out.strip() == "4"


def test_overview_lists_all_tasks(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(d, 1, title="Setup")
    write_task(d, 2, title="Auth", dependencies="[1]", complexity="7")
    assert tm.cmd_overview(d) == 0
    overview = (d / "overview.md").read_text(encoding="utf-8")
    assert "| 1 | Setup |" in overview
    assert "| 2 | Auth |" in overview
    assert "2 task(s)" in overview


def test_overview_counts_subtasks(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(
        d,
        1,
        body="\n## Subtasks\n### 1.1 first — status: pending\nx\n### 1.2 second\ny\n",
    )
    tm.cmd_overview(d)
    overview = (d / "overview.md").read_text(encoding="utf-8")
    # id | title | status | priority | deps | complexity | subtasks(2)
    assert "| 2 |" in overview.split("\n")[-2]


def test_validate_ok(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(d, 1)
    write_task(d, 2, dependencies="[1]")
    assert tm.cmd_validate(d) == 0


def test_validate_missing_dependency(tmp_path, capsys):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(d, 1, dependencies="[9]")
    assert tm.cmd_validate(d) == 1
    assert "missing id 9" in capsys.readouterr().err


def test_validate_forward_dependency(tmp_path, capsys):
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(d, 1, dependencies="[2]")
    write_task(d, 2)
    assert tm.cmd_validate(d) == 1
    assert "not lower" in capsys.readouterr().err


def test_validate_detects_cycle(tmp_path, capsys):
    # Force a cycle by hand (1 -> 2 and 2 -> 1), bypassing the lower-id rule check ordering.
    d = tmp_path / "tasks"
    d.mkdir()
    write_task(d, 1, dependencies="[2]")
    write_task(d, 2, dependencies="[1]")
    assert tm.cmd_validate(d) == 1
    err = capsys.readouterr().err
    assert "cycle" in err


def test_duplicate_id_rejected(tmp_path):
    d = tmp_path / "tasks"
    d.mkdir()
    (d / "001-a.md").write_text("---\nid: 1\ntitle: A\n---\n", encoding="utf-8")
    (d / "001-b.md").write_text("---\nid: 1\ntitle: B\n---\n", encoding="utf-8")
    with pytest.raises(tm.TaskError):
        tm.load_tasks(d)

from pathlib import Path

from task_cli.store import TaskStore


def test_add_persists_task(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")

    created = store.add("write tests")

    assert created["id"] == 1
    assert created["done"] is False
    assert store.list_tasks() == [
        {"id": 1, "title": "write tests", "done": False}
    ]


def test_done_command_slice_should_mark_task_complete(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    store.add("ship first slice")

    tasks = store.list_tasks()

    assert tasks[0]["done"] is False

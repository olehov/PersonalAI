"""Small JSON-backed task store used by benchmark prompts."""

from __future__ import annotations

import json
from pathlib import Path


class TaskStore:
    """Persists a list of task dictionaries to a JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[dict[str, object]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def save(self, tasks: list[dict[str, object]]) -> None:
        self._path.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, title: str) -> dict[str, object]:
        tasks = self.load()
        task = {
            "id": len(tasks) + 1,
            "title": title,
            "done": False,
        }
        tasks.append(task)
        self.save(tasks)
        return task

    def list_tasks(self) -> list[dict[str, object]]:
        return self.load()

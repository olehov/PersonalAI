"""Load and validate repo-aware benchmark packs for model evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepoBenchmarkTurn:
    """One follow-up turn inside a multi-turn benchmark task."""

    prompt: str
    expected_signals: tuple[str, ...] = field(default_factory=tuple)
    anti_signals: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RepoBenchmarkTask:
    """One repeatable benchmark scenario for repo-aware agent evaluation."""

    task_id: str
    category: str
    title: str
    objective: str
    workflow: str
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    prompt: str = ""
    expected_signals: tuple[str, ...] = field(default_factory=tuple)
    anti_signals: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    turns: tuple[RepoBenchmarkTurn, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RepoBenchmarkPack:
    """A named collection of repo-aware benchmark scenarios."""

    pack_id: str
    title: str
    description: str
    tasks: tuple[RepoBenchmarkTask, ...] = field(default_factory=tuple)


class BenchmarkPackService:
    """Reads benchmark pack JSON files into validated dataclass objects."""

    def load_pack(self, pack_path: Path) -> RepoBenchmarkPack:
        """Load a benchmark pack from JSON."""
        payload = json.loads(pack_path.read_text(encoding="utf-8"))
        tasks = tuple(self._parse_task(item) for item in payload.get("tasks", ()))
        return RepoBenchmarkPack(
            pack_id=str(payload["pack_id"]),
            title=str(payload["title"]),
            description=str(payload["description"]),
            tasks=tasks,
        )

    def serialize_pack(self, pack: RepoBenchmarkPack) -> dict[str, object]:
        """Convert a benchmark pack to a JSON-friendly dictionary."""
        return {
            "pack_id": pack.pack_id,
            "title": pack.title,
            "description": pack.description,
            "tasks": [
                {
                    "task_id": task.task_id,
                    "category": task.category,
                    "title": task.title,
                    "objective": task.objective,
                    "workflow": task.workflow,
                    "scope_dirs": list(task.scope_dirs),
                    "prompt": task.prompt,
                    "expected_signals": list(task.expected_signals),
                    "anti_signals": list(task.anti_signals),
                    "notes": list(task.notes),
                    "turns": [
                        {
                            "prompt": turn.prompt,
                            "expected_signals": list(turn.expected_signals),
                            "anti_signals": list(turn.anti_signals),
                            "notes": list(turn.notes),
                        }
                        for turn in task.turns
                    ],
                }
                for task in pack.tasks
            ],
        }

    def _parse_task(self, payload: dict[str, object]) -> RepoBenchmarkTask:
        return RepoBenchmarkTask(
            task_id=str(payload["task_id"]),
            category=str(payload["category"]),
            title=str(payload["title"]),
            objective=str(payload["objective"]),
            workflow=str(payload["workflow"]),
            scope_dirs=tuple(str(item) for item in payload.get("scope_dirs", ())),
            prompt=str(payload.get("prompt", "")),
            expected_signals=tuple(str(item) for item in payload.get("expected_signals", ())),
            anti_signals=tuple(str(item) for item in payload.get("anti_signals", ())),
            notes=tuple(str(item) for item in payload.get("notes", ())),
            turns=tuple(
                self._parse_turn(item)
                for item in payload.get("turns", ())
            ),
        )

    def _parse_turn(self, payload: dict[str, object]) -> RepoBenchmarkTurn:
        return RepoBenchmarkTurn(
            prompt=str(payload["prompt"]),
            expected_signals=tuple(str(item) for item in payload.get("expected_signals", ())),
            anti_signals=tuple(str(item) for item in payload.get("anti_signals", ())),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )


__all__ = [
    "BenchmarkPackService",
    "RepoBenchmarkPack",
    "RepoBenchmarkTask",
    "RepoBenchmarkTurn",
]

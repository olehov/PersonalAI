"""Classification helpers for retrieval note weighting."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

NoteClass = Literal[
    "reference",
    "project_note",
    "project_meta",
    "bridge",
    "meta",
]

_PROJECT_META_NAMES = {
    "project index.md",
    "readme.md",
    "mvp.md",
    "roadmap.md",
    "vision.md",
    "technology stack.md",
}

_REFERENCE_DIRS = {
    "algorithms",
    "bugs",
    "design patterns",
    "languages",
    "linux",
    "networking",
    "optimizations",
}

_BRIDGE_TITLES = {
    "observability.md",
    "caching.md",
    "retries and timeouts.md",
    "queues and backpressure.md",
}

_BRIDGE_DIRS = {
    "architecture decisions",
    "optimizations",
    "bugs",
    "design patterns",
}


def is_bridge_note(path: Path) -> bool:
    lower_parts = [part.casefold() for part in path.parts]
    return lower_parts[-1] in _BRIDGE_TITLES or any(
        part in _BRIDGE_DIRS for part in lower_parts[:-1]
    )


def classify_note(path: Path) -> NoteClass:
    """Classify a note into a small retrieval-oriented note family."""
    lower_parts = [part.casefold() for part in path.parts]
    lower_name = lower_parts[-1]
    parent_dirs = set(lower_parts[:-1])

    if lower_name in _PROJECT_META_NAMES:
        if "projects" in parent_dirs or "architecture decisions" in parent_dirs:
            return "project_meta"
        return "meta"

    if is_bridge_note(path):
        return "bridge"

    if "projects" in parent_dirs:
        return "project_note"

    if parent_dirs & _REFERENCE_DIRS:
        return "reference"

    return "meta"


def note_class_bonus(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    """Return a task-aware weighting bonus for the note class."""
    note_class = classify_note(path)
    task_mode = str(profile["task_mode"])
    preferred_dirs: set[str] = profile["preferred_dirs"]
    focused_coding = bool(profile["focused_coding"])
    cross_domain = bool(profile["cross_domain"])

    bonus = 0
    if task_mode == "implementation":
        if note_class == "reference":
            bonus += 10
        elif note_class == "project_note":
            bonus += 6
        elif note_class == "bridge":
            bonus += 2 if cross_domain else -4
        elif note_class == "project_meta":
            bonus -= 18
        else:
            bonus -= 4
    else:
        if note_class == "reference":
            bonus += 3 if focused_coding else 1
        elif note_class == "project_note":
            bonus += 3 if "projects" in preferred_dirs else 0
        elif note_class == "project_meta":
            bonus += 5 if "projects" in preferred_dirs and not focused_coding else -2
        elif note_class == "bridge":
            bonus += 4 if cross_domain else -1

    if bonus:
        reasons.append(f"note class: {note_class}")
    return bonus


def note_class_name(path: Path) -> NoteClass:
    """Expose the retrieval class name for debug payloads."""
    return classify_note(path)

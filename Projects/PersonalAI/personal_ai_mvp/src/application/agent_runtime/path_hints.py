"""Repository-path hint parsing helpers for the agent runtime."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable


def extract_repo_like_paths(text: str) -> tuple[str, ...]:
    """Collect repository-relative path hints from free-form text."""
    matches = re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", text.replace("\\", "/"))
    normalized: list[str] = []
    for match in matches:
        cleaned = match.strip("./ ")
        if cleaned:
            normalized.append(cleaned)
    return tuple(dict.fromkeys(normalized))


def filter_repo_like_paths(
    text: str,
    *,
    resolved_repo_path: Path | None,
    files_only: bool,
    canonicalize_repo_path_hint: Callable[[str, Path | None, bool], str | None],
) -> tuple[str, ...]:
    """Return canonical repository-relative paths when they can be resolved safely."""
    filtered: list[str] = []
    for hint in extract_repo_like_paths(text):
        canonical = canonicalize_repo_path_hint(
            hint,
            resolved_repo_path,
            files_only,
        )
        if canonical is not None:
            filtered.append(canonical)
    deduped: dict[str, str] = {}
    for item in filtered:
        deduped.setdefault(item.casefold(), item)
    return tuple(deduped.values())

"""Shared helpers for grounding generated internal links against real vault notes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from personal_ai.domain.models import NoteDocument


def build_note_lookup(notes: Iterable[NoteDocument]) -> dict[str, str]:
    """Build a vault-wide lookup for canonical note titles and common path forms."""
    lookup: dict[str, str] = {}
    for note in notes:
        title = note.title
        lookup[title.casefold()] = title
        lookup[note.path.as_posix().casefold()] = title
        lookup[note.path.stem.casefold()] = title
        lookup[note.path.name.casefold()] = title
    return lookup


def sanitize_generated_links(text: str, note_lookup: dict[str, str]) -> str:
    """Normalize generated markdown and Obsidian links to existing vault titles only."""
    normalized = normalize_markdown_links(text, note_lookup)
    return normalize_obsidian_links(normalized, note_lookup)


def normalize_markdown_links(text: str, note_lookup: dict[str, str]) -> str:
    """Rewrite markdown links into grounded Obsidian links when the target exists."""

    def replace(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        target = match.group(2).strip()
        normalized_target, exists = normalize_link_target(target, note_lookup)
        if exists:
            if label and label != normalized_target:
                return f"[[{normalized_target}|{label}]]"
            return f"[[{normalized_target}]]"
        return label or normalized_target

    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", replace, text)


def normalize_obsidian_links(text: str, note_lookup: dict[str, str]) -> str:
    """Keep only Obsidian links that resolve to a real vault note."""

    def replace(match: re.Match[str]) -> str:
        inner = match.group(1)
        target, _separator, alias = inner.partition("|")
        normalized_target, exists = normalize_link_target(target, note_lookup)
        if not exists:
            return alias or normalized_target
        if alias:
            return f"[[{normalized_target}|{alias}]]"
        return f"[[{normalized_target}]]"

    return re.sub(r"\[\[([^\]]+)\]\]", replace, text)


def normalize_link_target(target: str, note_lookup: dict[str, str]) -> tuple[str, bool]:
    """Resolve common target forms like paths or filenames to canonical note titles."""
    stripped = target.strip()
    candidate = stripped.replace("\\", "/")
    key = candidate.casefold()
    if key in note_lookup:
        return note_lookup[key], True

    path = Path(candidate)
    stem = path.stem.casefold()
    if stem in note_lookup:
        return note_lookup[stem], True

    if path.suffix.lower() == ".md":
        return path.stem, False
    return stripped, False


def find_unsupported_obsidian_links(text: str, note_lookup: dict[str, str]) -> tuple[str, ...]:
    """Return unresolved Obsidian link targets while preserving encounter order."""
    unsupported: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
        inner = match.group(1)
        target, _separator, _alias = inner.partition("|")
        normalized_target, exists = normalize_link_target(target, note_lookup)
        if exists:
            continue
        candidate = normalized_target.strip()
        key = candidate.casefold()
        if not candidate or key in seen:
            continue
        seen.add(key)
        unsupported.append(candidate)
    return tuple(unsupported)

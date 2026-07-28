"""Excerpt and text-similarity helpers for grounded answer prompts."""

from __future__ import annotations

import re


def excerpt(
    content: str,
    question: str,
    *,
    max_lines: int = 8,
    max_chars: int = 700,
) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines() if line.strip()]
    if not lines:
        return ""

    question_tokens = tokens(question)
    excerpt_lines = best_excerpt_lines(lines, question_tokens, max_lines=max_lines)
    excerpt_text = "\n".join(excerpt_lines)
    if len(excerpt_text) > max_chars:
        return excerpt_text[: max_chars - 3].rstrip() + "..."
    return excerpt_text


def indent_block(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines()) if text else f"{prefix}(empty)"


def best_excerpt_lines(
    lines: list[str],
    question_tokens: set[str],
    *,
    max_lines: int,
) -> list[str]:
    if not question_tokens:
        return lines[:max_lines]

    scored = [
        (line_score(line, question_tokens), index)
        for index, line in enumerate(lines)
    ]
    best_score, best_index = max(scored, key=lambda item: (item[0], item[1]))
    if best_score <= 0:
        return lines[:max_lines]

    heading_index = nearest_heading_index(lines, best_index)
    if heading_index is None:
        start = max(best_index - 2, 0)
        end = min(start + max_lines, len(lines))
        return lines[start:end]

    next_heading_index = next_heading_index_after(lines, heading_index + 1)
    section_end = next_heading_index if next_heading_index is not None else len(lines)
    section = lines[heading_index:section_end]
    if len(section) <= max_lines:
        return section

    best_offset = best_index - heading_index
    tail_window = max_lines - 1
    tail_start = min(max(best_offset - 1, 0), max(len(section) - tail_window, 0))
    return [section[0], *section[1 + tail_start : 1 + tail_start + tail_window]]


def nearest_heading_index(lines: list[str], index: int) -> int | None:
    for cursor in range(index, -1, -1):
        if lines[cursor].lstrip().startswith("#"):
            return cursor
    return None


def next_heading_index_after(lines: list[str], start: int) -> int | None:
    for cursor in range(start, len(lines)):
        if lines[cursor].lstrip().startswith("#"):
            return cursor
    return None


def line_score(line: str, question_tokens: set[str]) -> int:
    line_tokens = tokens(line)
    overlap = len(line_tokens & question_tokens)
    if overlap <= 0:
        return 0

    stripped = line.lstrip()
    normalized = stripped.casefold()
    if normalized.startswith("## related notes"):
        return 0

    if stripped.startswith("- [[") and stripped.endswith("]]"):
        overlap = max(overlap - 1, 0)
        if overlap <= 0:
            return 0

    bonus = 1 if stripped.startswith("##") or stripped.startswith("###") else 0
    if "complexity" in line_tokens and "complexity" in question_tokens:
        bonus += 1
    if {"priority", "queue"} <= line_tokens and {"priority", "queue"} <= question_tokens:
        bonus += 1
    return overlap + bonus


def tokens(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "using",
        "what",
        "when",
        "where",
        "with",
    }
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_]{3,}", text.casefold())
        if token not in stopwords
    }


def similarity_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def looks_bridgey(note) -> bool:
    path = note.path.as_posix().casefold()
    return any(
        fragment in path
        for fragment in (
            "architecture decisions/",
            "optimizations/",
            "bugs/",
            "design patterns/",
        )
    )

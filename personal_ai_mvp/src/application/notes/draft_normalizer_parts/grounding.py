"""Grounding-sensitive text cleanup helpers for generated notes."""

from __future__ import annotations

import re


def prune_unsupported_clauses(text: str, grounded_tokens: set[str]) -> str:
    if not grounded_tokens:
        return text

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if stripped.startswith(("#", "- ", "```")) or re.fullmatch(r"-{3,}", stripped):
            cleaned_lines.append(line)
            continue

        clauses = [part.strip() for part in re.split(r",\s+", stripped) if part.strip()]
        if len(clauses) == 1:
            cleaned_lines.append(line)
            continue

        kept = [clauses[0]]
        for clause in clauses[1:]:
            if is_grounded_clause(clause, grounded_tokens):
                kept.append(clause)
        cleaned_lines.append(", ".join(kept))

    return "\n".join(cleaned_lines)


def is_grounded_clause(clause: str, grounded_tokens: set[str]) -> bool:
    tokens = content_tokens(clause)
    if len(tokens) < 4:
        return True

    overlap = len(tokens & grounded_tokens)
    return overlap >= max(2, len(tokens) // 3)


def content_tokens(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "we",
        "will",
        "with",
    }
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_]{3,}", text.casefold())
        if token not in stopwords
    }

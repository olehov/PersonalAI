"""Note-selection helpers for grounded answer preparation."""

from __future__ import annotations

from application.knowledge.answer_support.excerpting import (
    excerpt,
    looks_bridgey,
    similarity_ratio,
    tokens,
)
from domain.models import RetrievedNote

IMPLEMENTATION_KEYWORDS = {
    "build",
    "code",
    "create",
    "function",
    "generate",
    "implement",
    "implementation",
    "make",
    "method",
    "minishell",
    "program",
    "refactor",
    "script",
    "write",
}


def detect_task_mode(question: str) -> str:
    lowered = question.casefold()
    if any(keyword in lowered for keyword in IMPLEMENTATION_KEYWORDS):
        return "implementation"
    return "general"


def select_answer_primary_notes(
    primary_notes: tuple[RetrievedNote, ...],
    question: str,
    *,
    task_mode: str,
) -> tuple[RetrievedNote, ...]:
    if not primary_notes:
        return ()

    question_tokens = tokens(question)
    selected: list[RetrievedNote] = []
    limit = 3 if task_mode == "implementation" else 2

    for item in primary_notes:
        if len(selected) >= limit:
            break
        if not is_helpful_primary_note(item, question_tokens, selected):
            continue
        selected.append(item)

    return tuple(selected)


def select_answer_related_notes(
    primary_notes: tuple[RetrievedNote, ...],
    related_notes: tuple[RetrievedNote, ...],
    question: str,
    *,
    task_mode: str,
) -> tuple[RetrievedNote, ...]:
    if not related_notes:
        return ()

    question_tokens = tokens(question)
    primary_paths = {item.note.path for item in primary_notes}
    selected: list[RetrievedNote] = []
    seen_paths: set[str] = set()
    limit = 2 if task_mode == "implementation" else 3

    for item in related_notes:
        if len(selected) >= limit:
            break
        if item.note.path.as_posix() in seen_paths:
            continue
        if not is_helpful_related_note(item, question_tokens, primary_paths, selected):
            continue
        selected.append(item)
        seen_paths.add(item.note.path.as_posix())

    return tuple(selected)


def is_helpful_primary_note(
    candidate: RetrievedNote,
    question_tokens: set[str],
    selected: list[RetrievedNote],
) -> bool:
    candidate_excerpt = excerpt(candidate.note.content, " ".join(sorted(question_tokens)))
    candidate_terms = tokens(candidate_excerpt)
    overlap = len(candidate_terms & question_tokens)

    if not selected:
        return True

    if overlap == 0 and candidate.score < 20:
        return False

    for existing in selected:
        existing_excerpt = excerpt(existing.note.content, " ".join(sorted(question_tokens)))
        existing_terms = tokens(existing_excerpt)
        similarity = similarity_ratio(candidate_terms, existing_terms)
        if similarity >= 0.6 and candidate.score <= existing.score:
            return False

    return True


def is_helpful_related_note(
    candidate: RetrievedNote,
    question_tokens: set[str],
    primary_paths: set[object],
    selected: list[RetrievedNote],
) -> bool:
    candidate_terms = tokens(candidate.note.title + "\n" + candidate.note.content)
    overlap = len(candidate_terms & question_tokens)
    candidate_excerpt = excerpt(candidate.note.content, " ".join(sorted(question_tokens)))
    excerpt_terms = tokens(candidate_excerpt)

    if overlap == 0 and candidate.score < 30:
        return False

    if looks_bridgey(candidate.note) and overlap < 2 and candidate.score < 45:
        return False
    if looks_bridgey(candidate.note) and overlap <= 2 and candidate.score < 40:
        return False

    if any(
        similarity_ratio(
            excerpt_terms,
            tokens(excerpt(item.note.content, " ".join(sorted(question_tokens)))),
        )
        >= 0.7
        for item in selected
    ):
        return False

    if candidate.note.path in primary_paths:
        return False

    return True

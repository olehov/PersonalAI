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
    "create",
    "generate",
    "implement",
    "implementation",
    "make",
    "refactor",
    "write",
}

CODING_KEYWORDS = IMPLEMENTATION_KEYWORDS | {
    "algorithm",
    "allocator",
    "api",
    "bug",
    "cleanup",
    "compile",
    "debug",
    "edge",
    "executor",
    "flow",
    "header",
    "logic",
    "memory",
    "module",
    "ownership",
    "parser",
    "pipeline",
    "redirection",
    "slice",
    "struct",
    "tokenizer",
    "validation",
}

IMPLEMENTATION_TARGET_HINTS = {
    "code",
    "executor",
    "file",
    "files",
    "flow",
    "function",
    "functions",
    "header",
    "headers",
    "makefile",
    "method",
    "module",
    "modules",
    "parser",
    "program",
    "script",
    "skeleton",
    "source",
    "struct",
}


def detect_task_mode(question: str) -> str:
    lowered = question.casefold()
    if any(
        phrase in lowered
        for phrase in (
            "prepare knowledge for note",
            "improve note '",
            'improve note "',
            "write a note",
            "draft a note",
            "create a note",
            "generate a note",
            "maintenance refactor",
        )
    ):
        return "general"
    implementation_action = any(keyword in lowered for keyword in IMPLEMENTATION_KEYWORDS)
    implementation_target = any(keyword in lowered for keyword in IMPLEMENTATION_TARGET_HINTS)
    implementation_subject = any(
        hint in lowered
        for hint in (
            " in c",
            " in python",
            " in java",
            " in javascript",
            " in cpp",
            " in c++",
            "bsq",
            "minishell",
            " shell ",
        )
    )
    if implementation_action and (implementation_target or implementation_subject):
        return "implementation"
    if any(keyword in lowered for keyword in CODING_KEYWORDS):
        return "coding"
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
    if task_mode in {"implementation", "coding", "agent", "note_draft"}:
        limit = 3
    else:
        limit = 2

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
    if task_mode in {"implementation", "coding"}:
        limit = 2
    else:
        limit = 3

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

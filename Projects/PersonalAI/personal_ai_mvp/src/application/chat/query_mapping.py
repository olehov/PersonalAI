"""Lightweight semantic normalization for grounded English queries."""

from __future__ import annotations

from application.chat.text_normalization import repair_common_utf8_mojibake


_NOTE_HINTS = (
    "nodes",
    "node",
    "notes",
    "note",
)

_KNOWLEDGE_CONTEXT_HINTS = (
    "obsidian",
    "vault",
    "knowledge",
    "graph",
    "coverage",
    "missing",
    "directory",
    "slice",
    "analyze",
)

_TERMINOLOGY_CLARIFICATION = (
    "Terminology clarification: in this request, nodes means knowledge-base notes "
    "(Obsidian notes), not linked-list, tree, graph, or other data-structure nodes."
)


def normalize_knowledge_query(text: str) -> str:
    """Add note-vs-node clarification for English knowledge-base queries."""
    stripped = repair_common_utf8_mojibake(text.strip())
    if not stripped:
        return text

    lowered = stripped.casefold()
    if _TERMINOLOGY_CLARIFICATION.casefold() in lowered:
        return stripped

    has_note_hint = any(hint in lowered for hint in _NOTE_HINTS)
    has_knowledge_context = any(hint in lowered for hint in _KNOWLEDGE_CONTEXT_HINTS)
    if not has_note_hint or not has_knowledge_context:
        return stripped

    return f"{stripped}\n\n{_TERMINOLOGY_CLARIFICATION}"

"""Lightweight semantic normalization for ambiguous knowledge-base queries."""

from __future__ import annotations


_NOTE_HINTS = (
    "ноди",
    "нода",
    "нотатки",
    "нотатка",
    "notes",
    "note",
    # Backward-compatible mojibake forms still seen in older fixtures.
    "РЅРѕРґРё",
    "РЅРѕРґР°",
    "РЅРѕС‚Р°С‚РєРё",
    "РЅРѕС‚Р°С‚РєР°",
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
    "проаналізуй",
    "аналіз",
    "граф",
    "нотат",
    "що в нас є",
    "що ще",
    "чого не вистачає",
    "додати",
    # Backward-compatible mojibake forms still seen in older fixtures.
    "РїСЂРѕР°РЅР°Р»С–Р·СѓР№",
    "Р°РЅР°Р»С–Р·",
    "РіСЂР°С„",
    "РЅРѕС‚Р°С‚",
    "С‰Рѕ РІ РЅР°СЃ С”",
    "С‰Рѕ С‰Рµ",
    "С‡РѕРіРѕ РЅРµ РІРёСЃС‚Р°С‡Р°С”",
    "РґРѕРґР°С‚Рё",
)

_TERMINOLOGY_CLARIFICATION = (
    "Terminology clarification: in this request, nodes means knowledge-base notes "
    "(Obsidian notes), not linked-list, tree, graph, or other data-structure nodes."
)


def normalize_knowledge_query(text: str) -> str:
    """Add a note-vs-node clarification when the query is about vault knowledge."""
    stripped = text.strip()
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

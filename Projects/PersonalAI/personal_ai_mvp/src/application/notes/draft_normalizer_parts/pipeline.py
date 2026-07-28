"""Top-level normalization pipeline for generated note drafts."""

from __future__ import annotations

import re

from application.notes.draft_normalizer_parts.authority import (
    apply_authority_constraints,
    apply_template_constraints,
    normalize_house_style,
    re_collapse_authoritative_bullets,
)
from application.notes.draft_normalizer_parts.grounding import (
    prune_unsupported_clauses,
)
from application.notes.draft_normalizer_parts.sections import (
    canonicalize_known_sections,
    normalize_section_spacing,
    prune_structured_section_intros,
    restore_missing_authoritative_heading_blocks,
    strip_unsupported_diagnostic_sections,
    strip_unsupported_open_questions,
)
from application.notes.link_sanitizer import (
    normalize_markdown_links,
    normalize_obsidian_links,
)


def normalize_generated_note(
    raw_content: str,
    *,
    note_lookup: dict[str, str] | None = None,
    grounded_tokens: set[str] | None = None,
    authoritative_text: str | None = None,
) -> str:
    text = raw_content.strip()
    lines = text.splitlines()
    cleaned: list[str] = []
    skip_rest = False

    banned_prefixes = (
        "grounded context:",
        "maintenance note:",
        "maintenance commentary:",
        "note:",
    )
    banned_phrases = (
        "this note should be expanded",
        "this note should be improved",
        "this note should be refactored",
        "generated from a maintenance task",
        "maintenance process",
    )

    for line in lines:
        stripped = line.strip()
        lowered = stripped.casefold()

        if lowered.startswith(banned_prefixes):
            skip_rest = True
            continue
        if skip_rest:
            continue
        if any(phrase in lowered for phrase in banned_phrases):
            continue

        cleaned.append(line.rstrip())

    normalized = "\n".join(cleaned).strip()
    normalized = normalized.replace("\r\n", "\n")
    normalized = re.sub(r"(?m)^\* ", "- ", normalized)
    normalized = normalize_markdown_links(normalized, note_lookup or {})
    normalized = normalize_obsidian_links(normalized, note_lookup or {})
    normalized = prune_unsupported_clauses(normalized, grounded_tokens or set())
    normalized = apply_authority_constraints(
        normalized,
        authoritative_text=authoritative_text or "",
        grounded_tokens=grounded_tokens or set(),
    )
    normalized = strip_unsupported_open_questions(
        normalized,
        grounded_tokens=grounded_tokens or set(),
        authoritative_text=authoritative_text or "",
    )
    normalized = strip_unsupported_diagnostic_sections(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = apply_template_constraints(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = normalize_house_style(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = prune_structured_section_intros(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = canonicalize_known_sections(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = re_collapse_authoritative_bullets(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = restore_missing_authoritative_heading_blocks(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = normalize_section_spacing(normalized)
    normalized = strip_unsupported_open_questions(
        normalized,
        grounded_tokens=grounded_tokens or set(),
        authoritative_text=authoritative_text or "",
    )
    normalized = strip_unsupported_diagnostic_sections(
        normalized,
        authoritative_text=authoritative_text or "",
    )
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized + "\n"

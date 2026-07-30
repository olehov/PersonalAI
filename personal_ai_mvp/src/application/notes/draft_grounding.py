"""Grounding and isolated-note helpers for note draft workflows."""

from __future__ import annotations

import re
from pathlib import Path

from application.notes.draft_normalizer import (
    content_tokens,
    looks_structurally_weaker_than_authority,
)
from application.notes.mutation_service import NoteMutationService


def build_note_lookup(answer_bundle, vault_lookup: dict[str, str]) -> dict[str, str]:
    """Merge vault lookup entries with retrieval-grounded note aliases."""
    lookup = dict(vault_lookup)
    for item in answer_bundle.retrieval.primary_notes + answer_bundle.retrieval.related_notes:
        note = item.note
        lookup[note.path.as_posix().casefold()] = note.title
        lookup[note.path.stem.casefold()] = note.title
        lookup[note.title.casefold()] = note.title
    return lookup


def build_grounding_tokens(answer_bundle, extra_texts: tuple[str, ...]) -> set[str]:
    """Collect normalized grounding tokens from retrieved context and authoritative text."""
    tokens: set[str] = set()
    for item in answer_bundle.retrieval.primary_notes + answer_bundle.retrieval.related_notes:
        tokens.update(content_tokens(item.note.title))
        tokens.update(content_tokens(item.note.content))
    for text in extra_texts:
        tokens.update(content_tokens(text))
    return tokens


def candidate_note_titles(answer_bundle, *, exclude_title: str) -> tuple[str, ...]:
    """Pick a small set of related grounded note titles excluding the current note."""
    titles: list[str] = []
    seen: set[str] = {exclude_title.casefold()}
    for item in answer_bundle.retrieval.primary_notes + answer_bundle.retrieval.related_notes:
        title = item.note.title
        key = title.casefold()
        if key in seen:
            continue
        titles.append(title)
        seen.add(key)
    return tuple(titles[:5])


def extract_preserved_facts(content: str) -> tuple[str, ...]:
    """Extract a compact set of authoritative non-heading facts from a note."""
    facts: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        facts.append(stripped)
    return tuple(facts[:5])


def enrich_isolated_note_links(
    content: str,
    *,
    finding_kind: str,
    related_titles: tuple[str, ...],
) -> str:
    """Add a small Related Notes section when an isolated note has no internal links."""
    if finding_kind != "isolated_note":
        return content
    if not related_titles:
        return content
    if re.search(r"\[\[[^\]]+\]\]", content):
        return content

    selected_titles = related_titles[:2]
    section_lines = [
        "## Related Notes",
        "",
        *[f"- [[{title}]]" for title in selected_titles],
    ]
    stripped = content.rstrip()
    return f"{stripped}\n\n" + "\n".join(section_lines) + "\n"


def stabilize_isolated_note_content(
    content: str,
    *,
    finding_kind: str,
    authoritative_text: str,
) -> str:
    """Fall back to authoritative text when an isolated-note rewrite is structurally weaker."""
    if finding_kind != "isolated_note":
        return content
    if not authoritative_text.strip():
        return content

    normalized_authority = authoritative_text.strip() + "\n"
    if looks_structurally_weaker_than_authority(content, authoritative_text):
        return normalized_authority
    return content


def build_isolated_companion_proposals(
    *,
    finding,
    answer_bundle,
    mutation_service: NoteMutationService,
):
    """Propose backlink refactors for a couple of grounded related notes when needed."""
    if finding.kind != "isolated_note":
        return ()

    proposals = []
    target_title = finding.note.title
    target_link = f"[[{target_title}]]"
    seen_paths: set[Path] = set()
    for item in answer_bundle.retrieval.primary_notes + answer_bundle.retrieval.related_notes:
        note = item.note
        if note.path == finding.note.path or note.path in seen_paths:
            continue
        seen_paths.add(note.path)

        if target_link in note.content:
            continue

        proposed_content = append_related_note_link(note.content, target_title)
        proposal = mutation_service.propose_change(
            title=note.title,
            proposed_content=proposed_content,
            action="refactor",
            target_path=note.path.as_posix(),
        )
        proposals.append(proposal)
        if len(proposals) >= 2:
            break

    return tuple(proposals)


def append_related_note_link(content: str, related_title: str) -> str:
    """Append a related-note link, creating a section when needed."""
    stripped = content.rstrip()
    if not stripped:
        return f"## Related Notes\n\n- [[{related_title}]]\n"

    if re.search(r"(?im)^## Related Notes\s*$", stripped):
        return stripped + f"\n- [[{related_title}]]\n"

    return stripped + f"\n\n## Related Notes\n\n- [[{related_title}]]\n"

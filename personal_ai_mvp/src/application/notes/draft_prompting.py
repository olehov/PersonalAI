"""Prompt-building helpers for grounded note drafting."""

from __future__ import annotations

from pathlib import Path

from application.shared.prompt_style import (
    build_prompt_style_pack,
    render_prompt_style_pack,
)
from domain.models import (
    AnswerBundle,
    KnowledgeMaintenanceFinding,
    PromptMessage,
    RetrievalBundle,
    RetrievedNote,
)


def derive_scope(*, target_dir: str | None, target_path: str | None) -> tuple[str, ...]:
    if target_dir:
        return (Path(target_dir).parts[0],) if Path(target_dir).parts else ()
    if target_path:
        path = Path(target_path)
        return (path.parts[0],) if path.parts else ()
    return ()


def render_style_guide(
    *,
    answer_bundle: AnswerBundle,
    authoritative_text: str,
) -> str:
    style_pack = build_prompt_style_pack(
        notes=tuple(
            item.note for item in answer_bundle.retrieval.primary_notes + answer_bundle.retrieval.related_notes
        ),
        authoritative_text=authoritative_text,
    )
    return render_prompt_style_pack(style_pack)


def build_draft_prompt(
    *,
    title: str,
    instruction: str,
    target_path: str | None,
    answer_context: str,
    style_guide: str,
) -> str:
    lines = [
        f"Target note title: {title}",
        f"Requested operation path hint: {target_path or '(auto)'}",
        f"User instruction: {instruction}",
        "Formatting requirements:",
        "- Start with a level-1 heading using the note title.",
        "- Use markdown only.",
        "- Prefer compact sections and bullet lists where useful.",
        "- Add relevant internal Obsidian links using [[Note Title]] when related notes exist in context.",
        "- If context is incomplete, include a short 'Open Questions' section.",
        "",
        style_guide,
        "",
        "Grounded context:",
        answer_context,
    ]
    return "\n".join(lines)


def build_maintenance_prompt(
    *,
    finding: KnowledgeMaintenanceFinding,
    answer_context: str,
    citations: tuple[str, ...],
    related_titles: tuple[str, ...],
    style_guide: str,
    preserved_facts: tuple[str, ...],
) -> str:
    lines = [
        f"Target note title: {finding.note.title}",
        f"Target note path: {finding.note.path.as_posix()}",
        f"Maintenance finding kind: {finding.kind}",
        f"Maintenance summary: {finding.summary}",
        "Maintenance details:",
        *[f"- {detail}" for detail in finding.details],
        "Refactor goals:",
        "- Keep the note grounded in the provided context.",
        "- Improve structure, clarity, and usefulness.",
        "- Preserve valid existing knowledge when still relevant.",
        "- Treat the current note as authoritative for existing facts and responsibility labels unless grounded context clearly corrects them.",
        "- Add relevant internal Obsidian links using [[Note Title]] when supported by context.",
        "- If the note is isolated, prefer adding at least one grounded internal link to a closely related note.",
        "- Keep a short Open Questions section only if important gaps remain.",
        "- Do not mention the maintenance process itself inside the note.",
        "- Do not introduce new claims unless they are supported by the current note or grounded context.",
        "- If the current note uses short bullets or labels, prefer preserving that compact style over expanding them into prose without strong support.",
    ]
    if preserved_facts:
        lines.extend(
            [
                "Facts to preserve if still correct:",
                *[f"- {fact}" for fact in preserved_facts],
            ]
        )
    if related_titles:
        lines.extend(
            [
                "Preferred internal links when relevant:",
                *[f"- [[{title}]]" for title in related_titles],
            ]
        )
    if citations:
        lines.extend(
            [
                "Grounded note paths:",
                *[f"- {path}" for path in citations],
            ]
        )
    lines.extend(
        [
            "",
            style_guide,
            "",
            "Current note content:",
            finding.note.content,
            "",
            "Grounded context:",
            answer_context,
        ]
    )
    return "\n".join(lines)


def refine_maintenance_answer_bundle(
    answer_bundle: AnswerBundle,
    target_path: Path,
) -> AnswerBundle:
    retrieval = answer_bundle.retrieval
    pooled_notes = merge_retrieved_notes(
        retrieval.primary_notes + retrieval.related_notes
    )
    ordered_notes = select_maintenance_notes(
        pooled_notes,
        target_path=target_path,
        limit=4,
    )
    selected_primary = tuple(
        item for item in ordered_notes
        if item.note.path == target_path
    )
    supplemental = tuple(
        item for item in ordered_notes
        if item.note.path != target_path
    )
    if not selected_primary and ordered_notes:
        selected_primary = ordered_notes[:1]
        supplemental = ordered_notes[1:]
    selected_primary = tuple([*selected_primary, *supplemental[:1]])[:2]
    primary_paths = {item.note.path for item in selected_primary}
    selected_related = tuple(
        item for item in supplemental
        if item.note.path not in primary_paths
    )[:2]
    filtered_retrieval = RetrievalBundle(
        question=retrieval.question,
        primary_notes=selected_primary,
        related_notes=selected_related,
    )
    filtered_citations = tuple(
        item.note.path.as_posix()
        for item in filtered_retrieval.primary_notes + filtered_retrieval.related_notes
    )
    return AnswerBundle(
        question=answer_bundle.question,
        retrieval=filtered_retrieval,
        messages=(
            answer_bundle.messages[0],
            PromptMessage(role="user", content=render_answer_context(filtered_retrieval)),
        ),
        citations=filtered_citations,
    )


def render_answer_context(bundle: RetrievalBundle) -> str:
    sections = [
        f"Question:\n{bundle.question}",
        "Instructions:\n- Ground the answer in the provided notes.\n- Cite note paths inline.\n- Say when knowledge is missing.",
        render_context_section("Primary Notes", bundle.primary_notes),
        render_context_section("Related Notes", bundle.related_notes),
    ]
    return "\n\n".join(section for section in sections if section)


def render_context_section(title: str, notes: tuple[RetrievedNote, ...]) -> str:
    if not notes:
        return f"{title}:\n- none"

    chunks = [f"{title}:"]
    for item in notes:
        chunks.append(
            "\n".join(
                [
                    f"- path: {item.note.path.as_posix()}",
                    f"  title: {item.note.title}",
                    f"  score: {item.score}",
                    f"  reason: {item.reason}",
                    "  excerpt:",
                    indent_block(note_excerpt(item.note.content)),
                ]
            )
        )
    return "\n".join(chunks)


def indent_block(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines()) if text else f"{prefix}(empty)"


def note_excerpt(content: str, *, max_lines: int = 6) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def select_maintenance_notes(
    notes: tuple[RetrievedNote, ...],
    *,
    target_path: Path,
    limit: int,
) -> tuple[RetrievedNote, ...]:
    if limit <= 0 or not notes:
        return ()

    selected: list[RetrievedNote] = []
    seen_paths: set[Path] = set()
    ordered = sorted(
        notes,
        key=lambda item: (
            maintenance_note_priority(item.note.path, target_path),
            -item.score,
            item.note.path.as_posix(),
        ),
    )
    for item in ordered:
        if len(selected) >= limit:
            break
        if item.note.path in seen_paths:
            continue
        if is_maintenance_noise(item.note.path, target_path, ordered):
            continue
        selected.append(item)
        seen_paths.add(item.note.path)
    return tuple(selected)


def merge_retrieved_notes(notes: tuple[RetrievedNote, ...]) -> tuple[RetrievedNote, ...]:
    merged: dict[Path, RetrievedNote] = {}
    for item in notes:
        existing = merged.get(item.note.path)
        if existing is None or item.score > existing.score:
            merged[item.note.path] = item
    return tuple(merged.values())


def maintenance_note_priority(path: Path, target_path: Path) -> tuple[int, int, str]:
    if path == target_path:
        return (0, 0, path.as_posix())

    same_parent = int(path.parent != target_path.parent)
    same_cluster = int(cluster_key(path) != cluster_key(target_path))
    mvp_penalty = 1 if "personal_ai_mvp" in {part.casefold() for part in path.parts} else 0
    return (same_parent, same_cluster + mvp_penalty, path.as_posix())


def cluster_key(path: Path) -> tuple[str, ...]:
    if len(path.parts) >= 2:
        return tuple(part.casefold() for part in path.parts[:2])
    return tuple(part.casefold() for part in path.parts)


def is_maintenance_noise(path: Path, target_path: Path, ordered: list[RetrievedNote]) -> bool:
    lower_parts = {part.casefold() for part in path.parts}
    if "personal_ai_mvp" not in lower_parts:
        return False

    target_cluster = cluster_key(target_path)
    has_non_mvp_cluster_note = any(
        cluster_key(item.note.path) == target_cluster
        and "personal_ai_mvp" not in {part.casefold() for part in item.note.path.parts}
        and item.note.path != target_path
        for item in ordered
    )
    return has_non_mvp_cluster_note

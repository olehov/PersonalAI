"""Helpers for building action-planning context inside the agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ActionPromptContextParts:
    """Shared prompt context assembled for action-specific drafting prompts."""

    notes_block: str
    citations: str
    file_tree_summary: str
    build_config_summary: str
    suggested_file_paths: tuple[str, ...]
    suggested_files: str
    related_files: str


def repo_summary_text(repo_summary: dict[str, str] | None) -> str:
    """Render a repository summary payload as compact text."""
    if repo_summary is None:
        return "none"
    return repo_summary["summary"]


def build_notes_block(
    retrieval_notes: dict[str, object],
    *,
    excerpt_builder: Callable[[str, int], str],
    excerpt_limit: int,
) -> str:
    """Build a compact preview block from the first grounded retrieval notes."""
    note_previews: list[str] = []
    for path, note in list(retrieval_notes.items())[:3]:
        note_previews.append(
            f"- {path} | {note.title} | excerpt={excerpt_builder(note.content, excerpt_limit)}"
        )
    return "\n".join(note_previews) if note_previews else "- none"


def suggest_first_slice_file_paths(
    *,
    action_target: str,
    request_text: str,
    resolved_repo_path: Path | None,
    find_repo_files: Callable[[Path, str, int], list[str]],
) -> tuple[str, ...]:
    """Suggest a small ordered set of likely first-slice file targets."""
    if resolved_repo_path is None:
        return ()

    candidates: list[str] = []
    preferred_patterns = ("parser", "token", "lex", "main", "shell")
    for pattern in preferred_patterns:
        candidates.extend(
            find_repo_files(resolved_repo_path, pattern, 2)
        )
    lowered_target = action_target.casefold()
    if "include" in lowered_target or ".h" in lowered_target:
        candidates.extend(
            find_repo_files(resolved_repo_path, ".h", 3)
        )
    if "src/parser" in lowered_target:
        candidates.extend(
            find_repo_files(resolved_repo_path, "parser", 3)
        )
    if "test" in request_text.casefold():
        candidates.extend(
            find_repo_files(resolved_repo_path, "test", 2)
        )
    if not candidates:
        candidates.extend(find_repo_files(resolved_repo_path, ".c", 4))
        candidates.extend(find_repo_files(resolved_repo_path, ".h", 2))

    return tuple(list(dict.fromkeys(candidates))[:6])


def render_file_list(paths: tuple[str, ...]) -> str:
    """Render file suggestions into the prompt-friendly bullet format."""
    if not paths:
        return "- none"
    return "\n".join(f"- {item}" for item in paths)


def build_related_file_summary(
    *,
    suggested_files: tuple[str, ...],
    resolved_repo_path: Path | None,
    find_repo_files: Callable[[Path, str, int], list[str]],
) -> str:
    """Derive nearby related files from the first-slice candidate set."""
    if resolved_repo_path is None:
        return "- none"

    related: list[str] = []
    for relative in suggested_files:
        path = Path(relative)
        stem = path.stem.casefold()
        for match in find_repo_files(resolved_repo_path, stem, 3):
            related.append(match)
    if not related:
        related.extend(find_repo_files(resolved_repo_path, "include", 2))
        related.extend(find_repo_files(resolved_repo_path, "src", 2))

    deduped = list(dict.fromkeys(related))[:6]
    if not deduped:
        return "- none"
    return "\n".join(f"- {item}" for item in deduped)


def build_action_prompt_context_parts(
    *,
    retrieval_notes: dict[str, object],
    citations: tuple[str, ...],
    resolved_repo_path: Path | None,
    build_file_tree_summary: Callable[[Path], str],
    build_config_summary: str | None,
    excerpt_builder: Callable[[str, int], str],
    excerpt_limit: int,
    action_target: str,
    request_text: str,
    find_repo_files: Callable[[Path, str, int], list[str]],
) -> ActionPromptContextParts:
    """Build the shared prompt fragments used by module-draft and patch-plan actions."""
    notes_block = build_notes_block(
        retrieval_notes,
        excerpt_builder=excerpt_builder,
        excerpt_limit=excerpt_limit,
    )
    rendered_citations = ", ".join(citations) if citations else "none"
    file_tree_summary = (
        build_file_tree_summary(resolved_repo_path)
        if resolved_repo_path is not None
        else "repo=none"
    )
    rendered_build_config_summary = build_config_summary or "repo=none\nmanifest=none"
    suggested_file_paths = suggest_first_slice_file_paths(
        action_target=action_target,
        request_text=request_text,
        resolved_repo_path=resolved_repo_path,
        find_repo_files=find_repo_files,
    )
    suggested_files = render_file_list(suggested_file_paths)
    related_files = build_related_file_summary(
        suggested_files=suggested_file_paths,
        resolved_repo_path=resolved_repo_path,
        find_repo_files=find_repo_files,
    )
    return ActionPromptContextParts(
        notes_block=notes_block,
        citations=rendered_citations,
        file_tree_summary=file_tree_summary,
        build_config_summary=rendered_build_config_summary,
        suggested_file_paths=suggested_file_paths,
        suggested_files=suggested_files,
        related_files=related_files,
    )

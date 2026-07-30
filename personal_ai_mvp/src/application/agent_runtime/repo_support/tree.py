"""Tree and search helpers for repository inspection."""

from __future__ import annotations

from pathlib import Path

from application.agent_runtime.repo_support.file_filters import (
    is_excluded_repo_context_file,
)


def build_file_tree_summary(repo_path: Path, *, vault_root: Path) -> str:
    lines = [f"repo={repo_path.relative_to(vault_root).as_posix()}"]
    lines.extend(collect_tree_lines(repo_path, depth=0, max_depth=2, max_entries=24))
    return "\n".join(lines)


def collect_tree_lines(
    directory: Path,
    *,
    depth: int,
    max_depth: int,
    max_entries: int,
) -> list[str]:
    if depth > max_depth or max_entries <= 0:
        return []
    try:
        entries = sorted(
            directory.iterdir(),
            key=lambda item: (not item.is_dir(), item.name.casefold()),
        )
    except OSError:
        return [f"{'  ' * depth}- [unreadable] {directory.name}"]

    lines: list[str] = []
    remaining = max_entries
    for entry in entries:
        if remaining <= 0:
            break
        prefix = "  " * depth
        marker = "[dir]" if entry.is_dir() else "[file]"
        lines.append(f"{prefix}- {marker} {entry.name}")
        remaining -= 1
        if entry.is_dir() and depth < max_depth and remaining > 0:
            child_lines = collect_tree_lines(
                entry,
                depth=depth + 1,
                max_depth=max_depth,
                max_entries=remaining,
            )
            lines.extend(child_lines)
            remaining -= len(child_lines)
    if len(entries) > len(lines):
        lines.append(f"{'  ' * depth}- ...")
    return lines


def find_repo_files(
    repo_path: Path,
    *,
    vault_root: Path,
    contains: str,
    limit: int,
) -> list[str]:
    matches: list[str] = []
    contains_lower = contains.casefold()
    for child in repo_path.rglob("*"):
        if len(matches) >= limit:
            break
        if not child.is_file():
            continue
        if is_excluded_repo_context_file(child):
            continue
        relative = child.relative_to(vault_root).as_posix()
        if contains_lower in relative.casefold():
            matches.append(relative)
    return matches


def find_repo_files_by_name(
    repo_path: Path,
    *,
    vault_root: Path,
    contains: str,
    limit: int,
) -> list[str]:
    matches: list[str] = []
    contains_lower = contains.casefold()
    for child in repo_path.rglob("*"):
        if len(matches) >= limit:
            break
        if not child.is_file():
            continue
        if is_excluded_repo_context_file(child):
            continue
        if contains_lower not in child.name.casefold():
            continue
        matches.append(child.relative_to(vault_root).as_posix())
    return matches

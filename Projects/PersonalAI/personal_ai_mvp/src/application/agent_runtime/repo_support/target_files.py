"""Target-file selection and snippet helpers for repository inspection."""

from __future__ import annotations

import re
from pathlib import Path

from application.agent_runtime.repo_support.file_filters import (
    SOURCE_LIKE_FILENAMES,
    is_excluded_repo_context_file,
    is_preferred_repo_context_file,
)
from application.agent_runtime.repo_support.tree import (
    find_repo_files,
    find_repo_files_by_name,
)

REQUEST_FILE_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("parser", "parsing", "parse", "quote", "quotes", "token", "tokenizer", "lexer", "lex", "split"), ("parser", "parsing", "parse", "token", "split", "lexer", "lex")),
    (("builtin", "builtins", "echo", "cd", "pwd", "export", "unset", "env", "exit"), ("builtin", "builtins", "echo", "cd", "pwd", "export", "unset", "env", "exit")),
    (("signal", "signals", "ctrl-c", "ctrl-d", "ctrl-\\"), ("signal", "signals", "prompt")),
    (("exec", "execve", "path", "fork", "pipe", "redirect", "redirection", "heredoc"), ("exec", "path", "pipe", "redir", "heredoc")),
)


def score_target_file_candidate(
    relative_path: str,
    *,
    request_text: str,
    planning_output: str,
) -> tuple[int, int, int, int, int, int, int, int, str]:
    normalized_path = relative_path.replace("\\", "/").casefold()
    file_path = Path(relative_path)
    source_text = f"{request_text}\n{planning_output}".casefold()

    request_bonus = 0
    for request_terms, file_terms in REQUEST_FILE_HINTS:
        if any(term in source_text for term in request_terms):
            if any(term in normalized_path for term in file_terms):
                request_bonus += 5

    explicit_name_bonus = 0
    stem = file_path.stem.casefold()
    for token in re.findall(r"[a-z0-9_#+.-]+", source_text):
        if len(token) >= 3 and (token == stem or token in normalized_path):
            explicit_name_bonus += 1

    is_preferred = int(is_preferred_repo_context_file(file_path))
    in_src_dir = int("/src/" in f"/{normalized_path}/" or normalized_path.startswith("src/"))
    in_include_dir = int("/include/" in f"/{normalized_path}/" or normalized_path.startswith("include/"))
    is_readme = int("readme" in file_path.name.casefold())
    is_manifest = int(file_path.name.casefold() in SOURCE_LIKE_FILENAMES)

    return (
        -request_bonus,
        -explicit_name_bonus,
        -is_preferred,
        -in_src_dir,
        -in_include_dir,
        is_readme,
        is_manifest,
        len(file_path.parts),
        normalized_path,
    )


def collect_target_file_snippets(
    *,
    resolved_repo_path: Path | None,
    request_text: str,
    planning_output: str,
    vault_root: Path,
    extract_repo_like_paths,
) -> dict[str, str]:
    if resolved_repo_path is None:
        return {}
    target_files = select_target_file_paths(
        resolved_repo_path=resolved_repo_path,
        request_text=request_text,
        planning_output=planning_output,
        vault_root=vault_root,
        extract_repo_like_paths=extract_repo_like_paths,
    )
    snippets: dict[str, str] = {}
    for relative_path in target_files:
        file_path = vault_root / relative_path
        snippet = read_file_snippet(file_path)
        if snippet:
            snippets[relative_path] = snippet
    return snippets


def select_target_file_paths(
    *,
    resolved_repo_path: Path,
    request_text: str,
    planning_output: str,
    vault_root: Path,
    extract_repo_like_paths,
) -> tuple[str, ...]:
    candidates: list[str] = []
    for path_hint in extract_repo_like_paths(f"{planning_output}\n{request_text}"):
        normalized_hint = path_hint.replace("\\", "/").strip("./ ")
        canonical = canonicalize_repo_path_hint(
            path_hint,
            vault_root=vault_root,
            resolved_repo_path=resolved_repo_path,
            files_only=True,
        )
        if canonical is not None:
            candidates.append(canonical)
            continue
        hint_path = Path(normalized_hint)
        if "/" in normalized_hint and hint_path.suffix == "":
            continue
        basename = hint_path.name.casefold()
        if basename:
            candidates.extend(
                find_repo_files(
                    resolved_repo_path,
                    vault_root=vault_root,
                    contains=basename,
                    limit=2,
                )
            )

    patterns = ("store", "cli", "parser", "token", "main", "shell")
    for pattern in patterns:
        candidates.extend(
            find_repo_files_by_name(
                resolved_repo_path,
                vault_root=vault_root,
                contains=pattern,
                limit=2,
            )
        )
        candidates.extend(
            find_repo_files(
                resolved_repo_path,
                vault_root=vault_root,
                contains=pattern,
                limit=2,
            )
        )

    deduped = list(dict.fromkeys(candidates))
    deduped = [
        item for item in deduped
        if not is_excluded_repo_context_file(Path(item))
    ]
    deduped.sort(
        key=lambda item: score_target_file_candidate(
            item,
            request_text=request_text,
            planning_output=planning_output,
        )
    )
    return tuple(deduped[:5])


def canonicalize_repo_path_hint(
    path_hint: str,
    *,
    vault_root: Path,
    resolved_repo_path: Path | None,
    files_only: bool,
) -> str | None:
    normalized = path_hint.replace("\\", "/").strip("./ ")
    if not normalized:
        return None
    direct = vault_root / normalized
    if direct.exists():
        if files_only and not direct.is_file():
            return None
        return direct.relative_to(vault_root).as_posix()
    if resolved_repo_path is not None:
        repo_relative = resolved_repo_path / normalized
        if repo_relative.exists():
            if files_only and not repo_relative.is_file():
                return None
            return repo_relative.relative_to(vault_root).as_posix()

        normalized_parts = tuple(part.casefold() for part in Path(normalized).parts if part)
        if normalized_parts:
            for child in resolved_repo_path.rglob("*"):
                if files_only and not child.is_file():
                    continue
                child_parts = child.relative_to(resolved_repo_path).parts
                if len(child_parts) < len(normalized_parts):
                    continue
                suffix = tuple(part.casefold() for part in child_parts[-len(normalized_parts):])
                if suffix == normalized_parts:
                    return child.relative_to(vault_root).as_posix()
    return None


def read_file_snippet(file_path: Path, *, max_lines: int = 40, max_chars: int = 1600) -> str:
    if is_excluded_repo_context_file(file_path):
        return ""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    lines = content.splitlines()
    excerpt = "\n".join(lines[:max_lines]).strip()
    if not excerpt:
        return "(empty file)"
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rstrip() + "\n..."
    return excerpt

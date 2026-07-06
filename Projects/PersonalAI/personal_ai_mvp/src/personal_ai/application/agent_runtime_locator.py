"""Repository location helpers for the agent runtime."""

from __future__ import annotations

import re
from pathlib import Path


STOP_KEYWORDS = {
    "build",
    "mandatory",
    "part",
    "project",
    "local",
    "folder",
    "implementation",
}


def resolve_repo_path(
    *,
    vault_root: Path,
    normalized_goal: str,
    request_text: str,
    scope_dirs: tuple[str, ...],
    citations: tuple[str, ...],
) -> Path | None:
    preferred_roots = [
        vault_root / scope_dir
        for scope_dir in scope_dirs
        if (vault_root / scope_dir).exists()
    ]
    if not preferred_roots:
        preferred_roots = [vault_root / "Projects", vault_root]

    lowered = f"{normalized_goal}\n{request_text}".casefold()
    keywords = [
        token
        for token in re.findall(r"[a-zA-Z0-9_+-]{4,}", lowered)
        if token not in STOP_KEYWORDS
    ]
    if "minishell" in lowered:
        keywords.insert(0, "minishell")
    path_hints = extract_request_path_hints(request_text, scope_dirs)
    citation_dir_hints = extract_citation_directory_hints(citations)
    candidate_dirs = collect_repo_candidates(preferred_roots)
    if not candidate_dirs:
        return None

    scored_candidates: list[tuple[int, Path]] = []
    for candidate in candidate_dirs:
        score = score_repo_candidate(
            candidate,
            vault_root=vault_root,
            keywords=keywords,
            path_hints=path_hints,
            citation_dir_hints=citation_dir_hints,
            scope_dirs=scope_dirs,
        )
        if score > 0:
            scored_candidates.append((score, candidate))

    if not scored_candidates:
        return None

    scored_candidates.sort(
        key=lambda item: (
            -item[0],
            len(item[1].relative_to(vault_root).parts),
            item[1].name.casefold(),
        )
    )
    return scored_candidates[0][1]


def extract_request_path_hints(
    request_text: str,
    scope_dirs: tuple[str, ...],
) -> tuple[str, ...]:
    hints: list[str] = []
    combined_patterns = (
        re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", request_text),
        re.findall(r"(?:[A-Za-z0-9_.-]+\\)+[A-Za-z0-9_.-]+", request_text),
    )
    for matches in combined_patterns:
        for raw_hint in matches:
            normalized = raw_hint.replace("\\", "/").strip("./ ")
            if not normalized:
                continue
            hints.append(normalized.casefold())
            parts = [part for part in normalized.split("/") if part]
            for width in range(1, min(4, len(parts)) + 1):
                hints.append("/".join(parts[-width:]).casefold())
    for scope_dir in scope_dirs:
        normalized = scope_dir.replace("\\", "/").strip("./ ")
        if normalized:
            hints.append(normalized.casefold())
    return tuple(dict.fromkeys(hints))


def extract_citation_directory_hints(
    citations: tuple[str, ...],
) -> tuple[str, ...]:
    hints: list[str] = []
    for citation in citations:
        path = Path(citation)
        stem = path.stem.casefold()
        if stem:
            hints.append(stem)
        if len(path.parts) > 1:
            for width in range(1, min(4, len(path.parts))):
                hint = "/".join(path.parts[:width]).casefold()
                if hint:
                    hints.append(hint)
            if path.parent.as_posix() != ".":
                hints.append(path.parent.as_posix().casefold())
    return tuple(dict.fromkeys(hints))


def collect_repo_candidates(preferred_roots: list[Path]) -> tuple[Path, ...]:
    candidates: list[Path] = []
    seen: set[Path] = set()
    for root in preferred_roots:
        if not root.exists():
            continue
        if root not in seen and root.is_dir():
            seen.add(root)
            candidates.append(root)
        for candidate in iter_candidate_dirs(root):
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return tuple(candidates)


def iter_candidate_dirs(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    try:
        direct_children = [item for item in root.iterdir() if item.is_dir()]
    except OSError:
        return ()
    for child in direct_children:
        candidates.append(child)
        try:
            nested_dirs = [item for item in child.iterdir() if item.is_dir()]
        except OSError:
            continue
        candidates.extend(nested_dirs)
    return tuple(candidates)


def score_repo_candidate(
    candidate: Path,
    *,
    vault_root: Path,
    keywords: list[str],
    path_hints: tuple[str, ...],
    citation_dir_hints: tuple[str, ...],
    scope_dirs: tuple[str, ...],
) -> int:
    relative_path = candidate.relative_to(vault_root).as_posix().casefold()
    name = candidate.name.casefold()
    score = 0

    for keyword in keywords:
        if keyword == name:
            score += 10
        elif keyword in name:
            score += 6
        elif keyword in relative_path:
            score += 3

    for hint in path_hints:
        if hint == relative_path:
            score += 14
        elif relative_path.endswith(hint):
            score += 10
        elif hint in relative_path:
            score += 4

    for hint in citation_dir_hints:
        if hint == name:
            score += 8
        elif hint in relative_path:
            score += 5

    if scope_dirs and any(relative_path.startswith(scope.casefold().strip("/")) for scope in scope_dirs):
        score += 3

    if (candidate / "Makefile").exists():
        score += 3
    if (candidate / "pyproject.toml").exists():
        score += 3
    if (candidate / "package.json").exists():
        score += 3
    if (candidate / "src").is_dir():
        score += 2
    if (candidate / "include").is_dir():
        score += 1
    return score

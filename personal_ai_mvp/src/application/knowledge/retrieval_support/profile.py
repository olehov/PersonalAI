"""Query profiling and tokenization helpers for retrieval."""

from __future__ import annotations

import re
from pathlib import Path

from domain.models import NoteDocument

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "while",
    "why",
    "with",
}

GENERIC_CODING_TOKENS = {
    "build",
    "built",
    "code",
    "coding",
    "create",
    "executor",
    "file",
    "files",
    "function",
    "functions",
    "generate",
    "header",
    "headers",
    "implement",
    "implementation",
    "makefile",
    "module",
    "modules",
    "parser",
    "program",
    "refactor",
    "shell",
    "single",
    "source",
    "standalone",
    "struct",
    "write",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_]{2,}", text.casefold())
        if token not in STOPWORDS
    }


def build_query_profile(
    question: str,
    tokens: set[str],
    scope_dirs: tuple[str, ...],
    *,
    task_mode: str = "general",
) -> dict[str, object]:
    normalized = question.casefold()
    preferred_dirs: set[str] = set()
    technical = False
    focused_coding = False
    strict_meta_filtering = task_mode in {"implementation", "coding", "note_draft"}

    topic_map = {
        "Algorithms": {"algorithm", "algorithms", "heap", "binary", "search", "graph", "tree", "dp"},
        "Linux": {"linux", "kernel", "bash", "shell", "systemd", "ubuntu", "debian"},
        "Networking": {"network", "networking", "tcp", "udp", "http", "dns", "socket"},
        "Languages": {"python", "javascript", "java", "cpp", "cxx", "c++"},
        "Design Patterns": {"pattern", "patterns", "factory", "strategy", "observer"},
        "Optimizations": {"optimization", "performance", "latency", "throughput"},
        "Bugs": {"bug", "bugs", "error", "crash", "fix", "incident"},
    }

    for directory, keywords in topic_map.items():
        if tokens & keywords:
            preferred_dirs.add(directory.casefold())
            technical = True

    if {"implementation", "complexity", "operations", "datastructure", "data", "structure"} & tokens:
        technical = True
        preferred_dirs.add("algorithms")

    if "code" in tokens or "engineering" in tokens:
        technical = True

    coding_hints = {
        "build",
        "code",
        "create",
        "executor",
        "file",
        "files",
        "function",
        "functions",
        "generate",
        "header",
        "headers",
        "implement",
        "implementation",
        "makefile",
        "module",
        "modules",
        "parser",
        "program",
        "refactor",
        "source",
        "struct",
        "write",
    }
    focused_coding = bool(tokens & coding_hints)
    if task_mode in {"implementation", "coding", "agent"}:
        focused_coding = True
    if strict_meta_filtering or task_mode == "agent":
        focused_coding = True
        technical = True
    if task_mode == "note_draft":
        technical = True
    if re.search(r"\bminishell\b", normalized):
        focused_coding = True
        preferred_dirs.add("projects")
    if re.search(r"\bbsq\b", normalized):
        focused_coding = True
        preferred_dirs.add("projects")
    if re.search(r"\bin c\b", normalized) or re.search(r"\bc program\b", normalized):
        focused_coding = True
        preferred_dirs.update({"languages", "c"})
    if "single-file" in normalized or "single file" in normalized:
        focused_coding = True

    references_personal_ai_project = (
        "personalai" in normalized
        or "personal ai" in normalized
        or "agent smith" in normalized
    )

    preferred_dirs.update(scope.casefold() for scope in scope_dirs if scope.strip())
    if preferred_dirs:
        technical = True

    bridge_keywords = {
        "observability",
        "debugging",
        "distributed",
        "resilience",
        "retries",
        "timeouts",
        "backpressure",
        "caching",
        "latency",
        "throughput",
        "reliability",
        "availability",
    }
    cross_domain = len(preferred_dirs) >= 2 or bool(tokens & bridge_keywords)

    focus_entities = {
        token
        for token in tokens
        if len(token) >= 3 and token not in GENERIC_CODING_TOKENS
    }
    for explicit_entity in ("bsq", "minishell"):
        if explicit_entity in normalized:
            focus_entities.add(explicit_entity)

    return {
        "task_mode": task_mode,
        "normalized_question": normalized,
        "preferred_dirs": preferred_dirs,
        "technical": technical,
        "cross_domain": cross_domain,
        "focused_coding": focused_coding,
        "strict_meta_filtering": strict_meta_filtering,
        "agent_mode": task_mode == "agent",
        "note_draft_mode": task_mode == "note_draft",
        "focus_entities": focus_entities,
        "references_personal_ai_project": references_personal_ai_project,
    }


def matches_scope(path: Path, normalized_scopes: tuple[str, ...]) -> bool:
    lower_parts = [part.casefold() for part in path.parts]
    for scope in normalized_scopes:
        scope_parts = [part for part in re.split(r"[\\/]+", scope.casefold()) if part]
        if not scope_parts:
            continue
        if len(scope_parts) == 1:
            if scope_parts[0] in lower_parts:
                return True
            continue
        window = len(scope_parts)
        for index in range(len(lower_parts) - window + 1):
            if lower_parts[index : index + window] == scope_parts:
                return True
    return False


def note_query_terms(note: NoteDocument, question_tokens: set[str]) -> set[str]:
    return note_selection_terms(note) & question_tokens


def note_selection_terms(note: NoteDocument) -> set[str]:
    return tokenize(" ".join((note.title, note.path.as_posix(), note.content)))


def related_query_terms(note: NoteDocument) -> set[str]:
    content = re.sub(r"\[\[[^\]]+\]\]", " ", note.content)
    return tokenize(" ".join((note.title, note.path.as_posix(), content)))


def term_overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0

    union = left | right
    if not union:
        return 0.0

    return len(left & right) / len(union)

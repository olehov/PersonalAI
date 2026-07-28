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


def build_query_profile(question: str, tokens: set[str], scope_dirs: tuple[str, ...]) -> dict[str, object]:
    normalized = question.casefold()
    preferred_dirs: set[str] = set()
    technical = False
    focused_coding = False

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
        "normalized_question": normalized,
        "preferred_dirs": preferred_dirs,
        "technical": technical,
        "cross_domain": cross_domain,
        "focused_coding": focused_coding,
        "focus_entities": focus_entities,
    }


def matches_scope(path: Path, normalized_scopes: tuple[str, ...]) -> bool:
    lower_parts = [part.casefold() for part in path.parts]
    return any(scope in lower_parts for scope in normalized_scopes)


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

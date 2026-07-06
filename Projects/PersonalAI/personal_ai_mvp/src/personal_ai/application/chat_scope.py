"""Scope and complexity helpers for the chat service."""

from __future__ import annotations

import re

from personal_ai.application.query_mapping import normalize_knowledge_query


def build_complexity_message() -> str:
    """Return a user-facing redirect for project-scale implementation prompts."""
    return (
        "This Ask request looks like a full agentic project-build task, not a compact grounded Q&A prompt. "
        "Use Ask for smaller technical questions, or switch to the Implementation Scope workflow. "
        "That mode breaks the request into smaller grounded implementation slices instead of trying to generate the whole project at once."
    )


def validate_question(
    question: str,
    *,
    project_scale_patterns: tuple[str, ...],
) -> None:
    """Reject agentic project-build prompts from the lightweight Ask workflow."""
    normalized = question.casefold()
    matched_patterns = sum(
        1 for pattern in project_scale_patterns if re.search(pattern, normalized)
    )
    if matched_patterns >= 2:
        raise ValueError(build_complexity_message())

    line_count = len([line for line in question.splitlines() if line.strip()])
    project_keywords = (
        "filesystem",
        "scaffold",
        "compile",
        "makefile",
        "build after changes",
        "fix compiler errors",
        "create project structure",
        "run a few basic validation commands",
    )
    keyword_hits = sum(1 for keyword in project_keywords if keyword in normalized)
    if line_count >= 12 and keyword_hits >= 3:
        raise ValueError(build_complexity_message())


def normalize_scope_question(question: str) -> str:
    """Extract a compact retrieval query from a long project-scale request."""
    stripped_lines = [line.strip() for line in question.splitlines() if line.strip()]
    for line in stripped_lines:
        lowered = line.casefold()
        if lowered.startswith("your task is to "):
            return normalize_knowledge_query(line)
        if "build the mandatory part" in lowered:
            return normalize_knowledge_query(line)
        if "implement the mandatory part" in lowered:
            return normalize_knowledge_query(line)
        if "minishell" in lowered:
            return normalize_knowledge_query(line)
    if stripped_lines:
        return normalize_knowledge_query(stripped_lines[0])
    return normalize_knowledge_query(question.strip())


def build_scoped_user_prompt(*, answer_context: str, original_question: str) -> str:
    """Build the scoping-mode user prompt for project-scale implementation requests."""
    return (
        f"{answer_context}\n\n"
        "Implementation Scope Contract:\n"
        "- Do not attempt to fully implement the whole project.\n"
        "- Treat this as a scoping and decomposition task for a coding agent.\n"
        "- Use exactly these top-level sections in this order: Goal, Constraints, Modules, Incremental Slices, First Slice, Validation.\n"
        "- Under Modules, name concrete files, components, or subsystems to build.\n"
        "- Under Incremental Slices, break the work into 3 to 6 slices that can be implemented one at a time.\n"
        "- Under First Slice, choose the safest first implementation step and state the exact outputs it should produce.\n"
        "- Under Validation, list the first commands, tests, or checks to run after that slice.\n"
        "- Keep the answer compact and implementation-oriented.\n"
        f"- Original project-scale request:\n{original_question.strip()}"
    )

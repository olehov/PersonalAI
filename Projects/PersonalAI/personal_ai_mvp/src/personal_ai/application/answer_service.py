"""Answer preparation layer for grounded LLM interactions."""

from __future__ import annotations

import re

from personal_ai.application.prompt_style import (
    build_prompt_style_pack,
    render_prompt_style_pack,
)
from personal_ai.application.query_mapping import normalize_knowledge_query
from personal_ai.application.retrieval_service import RetrievalService
from personal_ai.domain.models import AnswerBundle, PromptMessage, RetrievalBundle, RetrievedNote


class AnswerService:
    """Builds grounded prompt payloads from retrieval results."""

    SYSTEM_PROMPT = (
        "You are PersonalAI, a local-first software engineering assistant focused first on writing code, "
        "explaining implementation details, and turning knowledge into actionable engineering output. "
        "Answer using only the supplied vault context when possible. "
        "If the context is incomplete, say what is missing instead of inventing details. "
        "Prefer code-first, implementation-first responses over high-level theory. "
        "When the user asks how to build something, start with concrete structure, APIs, algorithms, or code steps. "
        "Reason carefully before answering: reconcile conflicting notes, compare plausible implementation options, "
        "and choose the most defensible answer supported by the retrieved context. "
        "Before finalizing, internally check for unsupported claims, missing edge cases, and places where the request likely needs a narrower assumption. "
        "Keep answers concise, technical, and grounded, and cite note paths when making claims."
    )
    _IMPLEMENTATION_KEYWORDS = {
        "build",
        "code",
        "create",
        "function",
        "generate",
        "implement",
        "implementation",
        "make",
        "method",
        "minishell",
        "program",
        "refactor",
        "script",
        "write",
    }

    HIGH_REASONING_APPENDIX = (
        "High Reasoning Mode:\n"
        "- Spend extra effort resolving ambiguity before answering.\n"
        "- Compare the strongest implementation options and reject weaker ones.\n"
        "- Surface hidden assumptions, edge cases, cleanup rules, and failure modes that could break a real implementation.\n"
        "- Prefer a precise, opinionated answer over a broad survey when the retrieved notes support a concrete choice."
    )

    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service

    def prepare_answer(
        self,
        question: str,
        *,
        primary_limit: int = 3,
        related_limit: int = 5,
        scope_dirs: tuple[str, ...] = (),
        reasoning_mode: str = "standard",
    ) -> AnswerBundle:
        """Builds a grounded answer payload for a user question."""
        normalized_question = normalize_knowledge_query(question)
        task_mode = self._detect_task_mode(normalized_question)
        effective_primary_limit = primary_limit + 1 if task_mode == "implementation" else primary_limit
        effective_related_limit = max(related_limit - 1, 3) if task_mode == "implementation" else related_limit
        retrieval = self._retrieval_service.build_context(
            normalized_question,
            primary_limit=effective_primary_limit,
            related_limit=effective_related_limit,
            scope_dirs=scope_dirs,
        )
        filtered_retrieval = RetrievalBundle(
            question=normalized_question,
            primary_notes=self._select_answer_primary_notes(
                retrieval.primary_notes,
                normalized_question,
                task_mode=task_mode,
            ),
            related_notes=self._select_answer_related_notes(
                retrieval.primary_notes,
                retrieval.related_notes,
                normalized_question,
                task_mode=task_mode,
            ),
        )
        messages = (
            PromptMessage(role="system", content=self._build_system_prompt(reasoning_mode)),
            PromptMessage(role="user", content=self._build_user_prompt(filtered_retrieval, task_mode, reasoning_mode)),
        )
        citations = tuple(self._collect_citations(filtered_retrieval))
        return AnswerBundle(
            question=question,
            retrieval=filtered_retrieval,
            task_mode=task_mode,
            messages=messages,
            citations=citations,
        )

    def _build_system_prompt(self, reasoning_mode: str) -> str:
        """Build the system prompt for the selected reasoning mode."""
        if reasoning_mode != "high":
            return self.SYSTEM_PROMPT
        return (
            f"{self.SYSTEM_PROMPT} "
            "Use a deeper reasoning pass for this request: validate the design choice against the retrieved notes, "
            "check likely failure paths, and avoid stopping at the first plausible answer."
        )

    def _build_user_prompt(self, retrieval: RetrievalBundle, task_mode: str, reasoning_mode: str) -> str:
        style_pack = build_prompt_style_pack(
            notes=tuple(
                item.note for item in retrieval.primary_notes + retrieval.related_notes
            ),
        )
        instructions = [
            "- Ground the answer in the provided notes.",
            "- Treat the user as asking for software implementation help first.",
            "- Start with code structure, function breakdown, data flow, or step-by-step implementation guidance when relevant.",
            "- Prefer concrete examples, code sketches, edge cases, and execution details over generic theory.",
            "- If the context does not support a full implementation, say what is missing and give the safest partial design.",
            "- Think through the problem before answering: identify the core constraint, then choose the most defensible implementation approach from the provided context.",
            "- When multiple designs are possible, briefly compare them and commit to one instead of staying generic.",
            "- Before answering, check that each major claim is supported by the retrieved notes or clearly marked as an inference.",
            "- Cite note paths inline.",
        ]
        if reasoning_mode == "high":
            instructions.extend(
                (
                    "- This request is in high reasoning mode: spend more effort choosing the strongest implementation path, not the fastest generic answer.",
                    "- Expose important tradeoffs and then commit to one concrete recommendation.",
                    "- Pull forward failure modes, invariants, and validation logic that would matter in real code.",
                )
            )
        if task_mode == "implementation":
            instructions.extend(
                (
                    "- This request is in implementation mode: lead with a concrete build plan or code skeleton.",
                    "- Name modules, functions, data structures, and execution order before broad explanation.",
                    "- Prefer pseudocode or real code snippets when the context is strong enough.",
                    "- Call out assumptions, failure paths, cleanup rules, and validation steps that would matter during real implementation.",
                )
            )
        response_contract = ""
        if task_mode == "implementation":
            response_contract = (
                "Response Contract:\n"
                "- Use exactly these top-level sections in this order: Architecture, Modules, Execution Flow, Edge Cases, Code Skeleton.\n"
                "- Under Architecture, give a compact implementation shape for the system.\n"
                "- Under Modules, list concrete files, structs, classes, or functions to create.\n"
                "- Under Execution Flow, describe the runtime path step by step.\n"
                "- Under Edge Cases, call out failure paths, validation, cleanup, and error handling.\n"
                "- Under Code Skeleton, provide pseudocode or real code when the notes are sufficient.\n"
                "- Make a concrete decision when multiple implementation paths exist; do not leave the design unresolved unless the notes are genuinely insufficient.\n"
                "- If a key design choice depends on an assumption, state that assumption explicitly in the relevant section.\n"
                "- Do not start with generic theory or motivational text."
            )
        sections = [
            f"Question:\n{retrieval.question}",
            "Task Mode:\n" + task_mode,
            "Reasoning Mode:\n" + reasoning_mode,
            "Instructions:\n" + "\n".join(instructions),
            response_contract,
            self.HIGH_REASONING_APPENDIX if reasoning_mode == "high" else "",
            render_prompt_style_pack(style_pack),
            self._format_context_section("Primary Notes", retrieval.primary_notes, retrieval.question),
            self._format_context_section("Related Notes", retrieval.related_notes, retrieval.question),
        ]
        return "\n\n".join(section for section in sections if section)

    def _format_context_section(
        self,
        title: str,
        notes: tuple[RetrievedNote, ...],
        question: str,
    ) -> str:
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
                        _indent_block(_excerpt(item.note.content, question)),
                    ]
                )
            )
        return "\n".join(chunks)

    def _collect_citations(self, retrieval: RetrievalBundle) -> list[str]:
        seen: set[str] = set()
        citations: list[str] = []
        for item in (*retrieval.primary_notes, *retrieval.related_notes):
            path = item.note.path.as_posix()
            if path in seen:
                continue
            citations.append(path)
            seen.add(path)
        return citations

    def _select_answer_primary_notes(
        self,
        primary_notes: tuple[RetrievedNote, ...],
        question: str,
        *,
        task_mode: str,
    ) -> tuple[RetrievedNote, ...]:
        if not primary_notes:
            return ()

        question_tokens = _tokens(question)
        selected: list[RetrievedNote] = []
        limit = 3 if task_mode == "implementation" else 2

        for item in primary_notes:
            if len(selected) >= limit:
                break
            if not self._is_helpful_primary_note(item, question_tokens, selected):
                continue
            selected.append(item)

        return tuple(selected)

    def _select_answer_related_notes(
        self,
        primary_notes: tuple[RetrievedNote, ...],
        related_notes: tuple[RetrievedNote, ...],
        question: str,
        *,
        task_mode: str,
    ) -> tuple[RetrievedNote, ...]:
        if not related_notes:
            return ()

        question_tokens = _tokens(question)
        primary_paths = {item.note.path for item in primary_notes}
        selected: list[RetrievedNote] = []
        seen_paths: set[str] = set()
        limit = 2 if task_mode == "implementation" else 3

        for item in related_notes:
            if len(selected) >= limit:
                break
            if item.note.path.as_posix() in seen_paths:
                continue
            if not self._is_helpful_related_note(item, question_tokens, primary_paths, selected):
                continue
            selected.append(item)
            seen_paths.add(item.note.path.as_posix())

        return tuple(selected)

    def _is_helpful_primary_note(
        self,
        candidate: RetrievedNote,
        question_tokens: set[str],
        selected: list[RetrievedNote],
    ) -> bool:
        candidate_excerpt = _excerpt(candidate.note.content, " ".join(sorted(question_tokens)))
        candidate_terms = _tokens(candidate_excerpt)
        overlap = len(candidate_terms & question_tokens)

        if not selected:
            return True

        if overlap == 0 and candidate.score < 20:
            return False

        for existing in selected:
            existing_excerpt = _excerpt(existing.note.content, " ".join(sorted(question_tokens)))
            existing_terms = _tokens(existing_excerpt)
            similarity = _similarity_ratio(candidate_terms, existing_terms)
            if similarity >= 0.6 and candidate.score <= existing.score:
                return False

        return True

    def _detect_task_mode(self, question: str) -> str:
        lowered = question.casefold()
        if any(keyword in lowered for keyword in self._IMPLEMENTATION_KEYWORDS):
            return "implementation"
        return "general"

    def _is_helpful_related_note(
        self,
        candidate: RetrievedNote,
        question_tokens: set[str],
        primary_paths: set[object],
        selected: list[RetrievedNote],
    ) -> bool:
        candidate_terms = _tokens(candidate.note.title + "\n" + candidate.note.content)
        overlap = len(candidate_terms & question_tokens)
        excerpt = _excerpt(candidate.note.content, " ".join(sorted(question_tokens)))
        excerpt_terms = _tokens(excerpt)

        if overlap == 0 and candidate.score < 30:
            return False

        if _looks_bridgey(candidate.note) and overlap < 2 and candidate.score < 45:
            return False
        if _looks_bridgey(candidate.note) and overlap <= 2 and candidate.score < 40:
            return False

        if any(_similarity_ratio(excerpt_terms, _tokens(_excerpt(item.note.content, " ".join(sorted(question_tokens))))) >= 0.7 for item in selected):
            return False

        if candidate.note.path in primary_paths:
            return False

        return True


def _excerpt(
    content: str,
    question: str,
    *,
    max_lines: int = 8,
    max_chars: int = 700,
) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines() if line.strip()]
    if not lines:
        return ""

    question_tokens = _tokens(question)
    excerpt_lines = _best_excerpt_lines(lines, question_tokens, max_lines=max_lines)
    excerpt = "\n".join(excerpt_lines)
    if len(excerpt) > max_chars:
        return excerpt[: max_chars - 3].rstrip() + "..."
    return excerpt


def _indent_block(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines()) if text else f"{prefix}(empty)"


def _best_excerpt_lines(
    lines: list[str],
    question_tokens: set[str],
    *,
    max_lines: int,
) -> list[str]:
    if not question_tokens:
        return lines[:max_lines]

    scored = [
        (_line_score(line, question_tokens), index)
        for index, line in enumerate(lines)
    ]
    best_score, best_index = max(scored, key=lambda item: (item[0], item[1]))
    if best_score <= 0:
        return lines[:max_lines]

    heading_index = _nearest_heading_index(lines, best_index)
    if heading_index is None:
        start = max(best_index - 2, 0)
        end = min(start + max_lines, len(lines))
        return lines[start:end]

    next_heading_index = _next_heading_index(lines, heading_index + 1)
    section_end = next_heading_index if next_heading_index is not None else len(lines)
    section = lines[heading_index:section_end]
    if len(section) <= max_lines:
        return section

    best_offset = best_index - heading_index
    tail_window = max_lines - 1
    tail_start = min(max(best_offset - 1, 0), max(len(section) - tail_window, 0))
    return [section[0], *section[1 + tail_start : 1 + tail_start + tail_window]]


def _nearest_heading_index(lines: list[str], index: int) -> int | None:
    for cursor in range(index, -1, -1):
        if lines[cursor].lstrip().startswith("#"):
            return cursor
    return None


def _next_heading_index(lines: list[str], start: int) -> int | None:
    for cursor in range(start, len(lines)):
        if lines[cursor].lstrip().startswith("#"):
            return cursor
    return None


def _line_score(line: str, question_tokens: set[str]) -> int:
    line_tokens = _tokens(line)
    overlap = len(line_tokens & question_tokens)
    if overlap <= 0:
        return 0

    stripped = line.lstrip()
    normalized = stripped.casefold()
    if normalized.startswith("## related notes"):
        return 0

    if stripped.startswith("- [[") and stripped.endswith("]]"):
        overlap = max(overlap - 1, 0)
        if overlap <= 0:
            return 0

    bonus = 1 if stripped.startswith("##") or stripped.startswith("###") else 0
    if "complexity" in line_tokens and "complexity" in question_tokens:
        bonus += 1
    if {"priority", "queue"} <= line_tokens and {"priority", "queue"} <= question_tokens:
        bonus += 1
    return overlap + bonus


def _tokens(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "using",
        "what",
        "when",
        "where",
        "with",
    }
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_]{3,}", text.casefold())
        if token not in stopwords
    }


def _looks_bridgey(note) -> bool:
    path = note.path.as_posix().casefold()
    return any(
        fragment in path
        for fragment in (
            "architecture decisions/",
            "optimizations/",
            "bugs/",
            "design patterns/",
        )
    )


def _similarity_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)

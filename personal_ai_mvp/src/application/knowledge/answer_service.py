"""Answer preparation layer for grounded LLM interactions."""

from __future__ import annotations

from application.chat.query_mapping import normalize_knowledge_query
from application.knowledge.answer_support.prompting import (
    build_system_prompt as _build_system_prompt,
    build_user_prompt as _build_user_prompt,
    collect_citations as _collect_citations,
)
from application.knowledge.answer_support.selection import (
    detect_task_mode as _detect_task_mode,
    is_helpful_primary_note as _is_helpful_primary_note,
    is_helpful_related_note as _is_helpful_related_note,
    select_answer_primary_notes as _select_answer_primary_notes,
    select_answer_related_notes as _select_answer_related_notes,
)
from application.knowledge.answer_support.excerpting import (
    excerpt as _excerpt,
    indent_block as _indent_block,
    looks_bridgey as _looks_bridgey,
    similarity_ratio as _similarity_ratio,
    tokens as _tokens,
)
from application.knowledge.retrieval_service import RetrievalService
from domain.models import AnswerBundle, PromptMessage, RetrievalBundle, RetrievedNote


class AnswerService:
    """Builds grounded prompt payloads from retrieval results."""

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
            task_mode=task_mode,
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
        return _build_system_prompt(reasoning_mode)

    def _build_user_prompt(self, retrieval: RetrievalBundle, task_mode: str, reasoning_mode: str) -> str:
        return _build_user_prompt(retrieval, task_mode, reasoning_mode)

    def _format_context_section(
        self,
        title: str,
        notes: tuple[RetrievedNote, ...],
        question: str,
    ) -> str:
        from application.knowledge.answer_support.prompting import format_context_section

        return format_context_section(title, notes, question)

    def _collect_citations(self, retrieval: RetrievalBundle) -> list[str]:
        return _collect_citations(retrieval)

    def _select_answer_primary_notes(
        self,
        primary_notes: tuple[RetrievedNote, ...],
        question: str,
        *,
        task_mode: str,
    ) -> tuple[RetrievedNote, ...]:
        return _select_answer_primary_notes(primary_notes, question, task_mode=task_mode)

    def _select_answer_related_notes(
        self,
        primary_notes: tuple[RetrievedNote, ...],
        related_notes: tuple[RetrievedNote, ...],
        question: str,
        *,
        task_mode: str,
    ) -> tuple[RetrievedNote, ...]:
        return _select_answer_related_notes(
            primary_notes,
            related_notes,
            question,
            task_mode=task_mode,
        )

    def _is_helpful_primary_note(
        self,
        candidate: RetrievedNote,
        question_tokens: set[str],
        selected: list[RetrievedNote],
    ) -> bool:
        return _is_helpful_primary_note(candidate, question_tokens, selected)

    def _detect_task_mode(self, question: str) -> str:
        return _detect_task_mode(question)

    def _is_helpful_related_note(
        self,
        candidate: RetrievedNote,
        question_tokens: set[str],
        primary_paths: set[object],
        selected: list[RetrievedNote],
    ) -> bool:
        return _is_helpful_related_note(candidate, question_tokens, primary_paths, selected)

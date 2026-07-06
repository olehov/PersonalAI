"""LLM-facing chat service built on top of grounded answer preparation."""

from __future__ import annotations

import re
from time import perf_counter

from personal_ai.application.answer_service import AnswerService
from personal_ai.application.chat_generation import (
    build_critique_messages as _build_critique_messages,
    build_refinement_messages as _build_refinement_messages,
    generate_answer_text as _generate_answer_text,
)
from personal_ai.application.chat_history import (
    compact_history_content as _compact_history_content,
    merge_conversation_history as _merge_conversation_history,
    normalize_conversation_history as _normalize_conversation_history,
)
from personal_ai.application.chat_scope import (
    build_complexity_message as _build_complexity_message,
    build_scoped_user_prompt as _build_scoped_user_prompt,
    normalize_scope_question as _normalize_scope_question,
    validate_question as _validate_question,
)
from personal_ai.domain.models import GeneratedAnswer, PromptMessage
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.env_loader import load_env_file, read_bool_env


class AskComplexityError(ValueError):
    """Raised when Ask receives a project-scale implementation request."""


class ChatService:
    """Runs grounded prompts through a local Ollama model."""

    _MAX_HISTORY_TURNS = 8
    _MAX_HISTORY_CHARS_PER_MESSAGE = 1_200
    _RECURSIVE_REFINEMENT_REASONING_MODES = {"high"}

    _PROJECT_SCALE_PATTERNS = (
        r"working inside my local project folder",
        r"act directly in the filesystem",
        r"create (?:the )?folders?, headers?, source files?, and makefile",
        r"compile and fix errors",
        r"keep going until (?:the project )?compiles",
        r"build the mandatory part",
        r"implement (?:the )?mandatory part",
        r"report final status truthfully",
        r"expected workflow:",
        r"output behavior:",
    )

    def __init__(
        self,
        answer_service: AnswerService,
        ollama_client: OllamaClient,
        history_repository=None,
        recursive_refinement_enabled: bool | None = None,
    ) -> None:
        self._answer_service = answer_service
        self._ollama_client = ollama_client
        self._history_repository = history_repository
        self._recursive_refinement_enabled = (
            self._default_recursive_refinement_enabled()
            if recursive_refinement_enabled is None
            else recursive_refinement_enabled
        )

    def ask(
        self,
        question: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
    ) -> GeneratedAnswer:
        """Builds a grounded prompt and sends it to Ollama."""
        self._validate_question(question)
        answer_bundle = self._answer_service.prepare_answer(
            question,
            scope_dirs=scope_dirs,
            reasoning_mode=reasoning_mode,
        )
        return self._run_prompt(
            question=question,
            model=model,
            scope_dirs=scope_dirs,
            answer_bundle=answer_bundle,
            messages=answer_bundle.messages,
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )

    def scope_implementation(
        self,
        question: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
    ) -> GeneratedAnswer:
        """Converts a project-scale implementation request into an incremental scoped plan."""
        normalized_question = self._normalize_scope_question(question)
        answer_bundle = self._answer_service.prepare_answer(
            normalized_question,
            scope_dirs=scope_dirs,
            reasoning_mode=reasoning_mode,
        )
        scoped_user_prompt = _build_scoped_user_prompt(
            answer_context=answer_bundle.messages[1].content,
            original_question=question,
        )
        return self._run_prompt(
            question=question,
            model=model,
            scope_dirs=scope_dirs,
            answer_bundle=answer_bundle,
            messages=(
                PromptMessage(role=answer_bundle.messages[0].role, content=answer_bundle.messages[0].content),
                PromptMessage(role="user", content=scoped_user_prompt),
            ),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )

    def _validate_question(self, question: str) -> None:
        try:
            _validate_question(
                question,
                project_scale_patterns=self._PROJECT_SCALE_PATTERNS,
            )
        except ValueError as exc:
            raise AskComplexityError(str(exc)) from exc

    def _build_complexity_message(self) -> str:
        return _build_complexity_message()

    def _normalize_scope_question(self, question: str) -> str:
        return _normalize_scope_question(question)

    def _run_prompt(
        self,
        *,
        question: str,
        model: str,
        scope_dirs: tuple[str, ...],
        answer_bundle,
        messages: tuple[PromptMessage, ...],
        conversation_history: tuple[PromptMessage, ...],
        reasoning_mode: str = "standard",
    ) -> GeneratedAnswer:
        """Send a prepared prompt through Ollama and persist history when configured."""
        normalized_messages = self._merge_conversation_history(
            tuple(
                PromptMessage(role=message.role, content=message.content)
                for message in messages
            ),
            conversation_history,
        )
        started_at = perf_counter()
        answer_text = self._generate_answer_text(
            model=model,
            messages=normalized_messages,
            reasoning_mode=reasoning_mode,
        )
        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        generated_answer = GeneratedAnswer(
            model=model,
            question=question,
            answer_text=answer_text,
            citations=answer_bundle.citations,
            prompt=answer_bundle,
        )
        if self._history_repository is not None:
            self._history_repository.save_generated_answer(
                generated_answer,
                scope_dirs=scope_dirs,
                latency_ms=latency_ms,
            )
        return generated_answer

    def _generate_answer_text(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        reasoning_mode: str,
    ) -> str:
        return _generate_answer_text(
            ollama_client=self._ollama_client,
            model=model,
            messages=messages,
            reasoning_mode=reasoning_mode,
            recursive_refinement_enabled=self._recursive_refinement_enabled,
            recursive_refinement_reasoning_modes=self._RECURSIVE_REFINEMENT_REASONING_MODES,
        )

    def _build_critique_messages(
        self,
        *,
        base_messages: tuple[PromptMessage, ...],
        draft_text: str,
    ) -> tuple[PromptMessage, ...]:
        return _build_critique_messages(
            base_messages=base_messages,
            draft_text=draft_text,
        )

    def _build_refinement_messages(
        self,
        *,
        base_messages: tuple[PromptMessage, ...],
        draft_text: str,
        critique_text: str,
    ) -> tuple[PromptMessage, ...]:
        return _build_refinement_messages(
            base_messages=base_messages,
            draft_text=draft_text,
            critique_text=critique_text,
        )

    @classmethod
    def _default_recursive_refinement_enabled(cls) -> bool:
        """Resolve whether recursive refinement is enabled from the environment."""
        load_env_file()
        fallback = read_bool_env("PERSONAL_AI_RECURSIVE_REFINEMENT", default=False)
        return read_bool_env(
            "PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT",
            default=fallback,
        )

    def _merge_conversation_history(
        self,
        base_messages: tuple[PromptMessage, ...],
        conversation_history: tuple[PromptMessage, ...],
    ) -> tuple[PromptMessage, ...]:
        return _merge_conversation_history(
            base_messages=base_messages,
            conversation_history=conversation_history,
            max_history_turns=self._MAX_HISTORY_TURNS,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

    def _normalize_conversation_history(
        self,
        conversation_history: tuple[PromptMessage, ...],
    ) -> tuple[PromptMessage, ...]:
        return _normalize_conversation_history(
            conversation_history,
            max_history_turns=self._MAX_HISTORY_TURNS,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

    def _compact_history_content(self, content: str) -> str:
        return _compact_history_content(
            content,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

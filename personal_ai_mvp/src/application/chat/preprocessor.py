"""Prompt preprocessing hook for translation and normalization stages."""

from __future__ import annotations

from dataclasses import dataclass

from application.chat.text_normalization import repair_common_utf8_mojibake
from domain.models import PromptMessage


@dataclass(frozen=True, slots=True)
class PromptPreprocessResult:
    """Structured preprocessing output for one inbound prompt."""

    original_text: str
    processed_text: str
    mode: str
    applied: bool = False
    translator_output: str | None = None
    translator_error: str | None = None
    fallback_reason: str | None = None


class PromptPreprocessor:
    """Prepare inbound prompts before routing or model dispatch."""

    _SUPPORTED_MODES = {"disabled", "translate_to_english"}
    _TRANSLATION_SYSTEM_PROMPT = (
        "You are a precise preprocessing translator for a local coding assistant. "
        "Translate the user prompt into concise, natural English for downstream routing and coding workflows. "
        "You do not have access to repository files, vault notes, local code, chat history, or external context. "
        "Use only the text provided in the current prompt. "
        "Preserve the exact intent, code terms, filenames, paths, commands, APIs, and error text. "
        "Do not explain the translation. Do not answer the request. Return only the translated prompt."
    )

    def __init__(
        self,
        *,
        mode: str = "disabled",
        model_client=None,
        translation_model: str | None = None,
        fallback_translation_model: str | None = None,
    ) -> None:
        normalized_mode = (mode or "disabled").strip().lower()
        if normalized_mode not in self._SUPPORTED_MODES:
            normalized_mode = "disabled"
        self._mode = normalized_mode
        self._model_client = model_client
        self._translation_model = (translation_model or "").strip() or None
        self._fallback_translation_model = (fallback_translation_model or "").strip() or None

    @property
    def mode(self) -> str:
        """Return the effective preprocessor mode."""
        return self._mode

    def preprocess(self, text: str, *, workflow_hint: str | None = None) -> PromptPreprocessResult:
        """Preprocess one prompt before routing or model dispatch."""
        original = text
        stripped = self._normalize_inbound_text(text)
        if self._mode == "disabled":
            return PromptPreprocessResult(
                original_text=original,
                processed_text=stripped or original,
                mode=self._mode,
                applied=False,
                translator_output=None,
                translator_error=None,
                fallback_reason=None,
            )

        if self._mode == "translate_to_english":
            return self._translate_to_english(original, stripped, workflow_hint=workflow_hint)

        return PromptPreprocessResult(
            original_text=original,
            processed_text=stripped or original,
            mode=self._mode,
            applied=False,
            translator_output=None,
            translator_error=None,
            fallback_reason=None,
        )

    def _translate_to_english(
        self,
        original: str,
        stripped: str,
        *,
        workflow_hint: str | None,
    ) -> PromptPreprocessResult:
        if not stripped:
            return PromptPreprocessResult(
                original_text=original,
                processed_text=original,
                mode=self._mode,
                applied=False,
                translator_output=None,
                translator_error=None,
                fallback_reason="empty_input",
            )
        if self._model_client is None or not self._translation_model:
            return PromptPreprocessResult(
                original_text=original,
                processed_text=stripped,
                mode=self._mode,
                applied=False,
                translator_output=None,
                translator_error=None,
                fallback_reason="translation_model_unavailable",
            )

        request_hint = workflow_hint or "general"
        messages = (
            PromptMessage(role="system", content=self._TRANSLATION_SYSTEM_PROMPT),
            PromptMessage(
                role="user",
                content=(
                    f"Workflow hint: {request_hint}\n"
                    "Translate this prompt to English for a coding assistant:\n"
                    f"{stripped}"
                ),
            ),
        )
        translated, translator_error, fallback_reason = self._translate_with_fallback(
            messages=messages,
        )

        processed = translated or stripped
        if not translated and fallback_reason is None:
            fallback_reason = "empty_translation_output"
        return PromptPreprocessResult(
            original_text=original,
            processed_text=processed,
            mode=self._mode,
            applied=bool(translated and translated != stripped),
            translator_output=translated or None,
            translator_error=translator_error,
            fallback_reason=fallback_reason,
        )

    def _translate_with_fallback(
        self,
        *,
        messages: tuple[PromptMessage, ...],
    ) -> tuple[str, str | None, str | None]:
        """Run translation through the primary model and optional fallback model."""
        primary_model = self._translation_model
        fallback_model = self._fallback_translation_model
        translator_error: str | None = None
        fallback_reason: str | None = None

        translated, primary_error = self._translate_once(primary_model, messages)
        if translated:
            return translated, None, None

        if primary_error:
            translator_error = primary_error
            fallback_reason = "translator_error"

        if fallback_model and fallback_model != primary_model:
            fallback_translated, fallback_error = self._translate_once(fallback_model, messages)
            if fallback_translated:
                return fallback_translated, translator_error, "fallback_model_applied"
            if fallback_error:
                if translator_error:
                    translator_error = f"{translator_error} | fallback: {fallback_error}"
                else:
                    translator_error = fallback_error
                fallback_reason = "fallback_model_error"
            elif fallback_reason is None:
                fallback_reason = "empty_translation_output"

        return "", translator_error, fallback_reason

    def _translate_once(
        self,
        model: str | None,
        messages: tuple[PromptMessage, ...],
    ) -> tuple[str, str | None]:
        """Run one translation attempt against one model."""
        if not model:
            return "", "translation model is not configured"
        try:
            translated = self._model_client.chat_with_options(
                model=model,
                messages=messages,
                options={"num_predict": 220},
            ).strip()
            return translated, None
        except Exception as exc:  # noqa: BLE001
            return "", self._build_error_preview(exc)

    def _build_error_preview(self, error: Exception) -> str:
        """Build a compact translator-error message for UI diagnostics."""
        message = str(error).strip() or error.__class__.__name__
        return message[:240]

    @classmethod
    def _normalize_inbound_text(cls, text: str) -> str:
        """Trim and repair common UTF-8 mojibake before routing or translation."""
        stripped = text.strip()
        if not stripped:
            return stripped
        return repair_common_utf8_mojibake(stripped)

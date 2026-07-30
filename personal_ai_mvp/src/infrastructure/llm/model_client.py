"""Shared protocol for model backends used across PersonalAI services."""

from __future__ import annotations

from typing import Protocol

from domain.models import PromptMessage


class ModelClient(Protocol):
    """Duck-typed LLM client contract used by application services."""

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        """Send a plain chat request."""

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        """Send a generation request with optional backend-specific options."""

    def list_models(self) -> list[str]:
        """Return models visible to the current backend."""


__all__ = [
    "ModelClient",
]

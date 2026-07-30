"""Route model requests between local Ollama and hosted OpenAI backends."""

from __future__ import annotations

from threading import RLock

from domain.models import PromptMessage


class RoutingModelClient:
    """Composite LLM client that dispatches by model namespace."""

    OPENAI_PREFIX = "openai:"

    def __init__(
        self,
        *,
        ollama_client,
        openai_client=None,
        serialize_ollama_requests: bool = True,
    ) -> None:
        self._ollama_client = ollama_client
        self._openai_client = openai_client
        self._serialize_ollama_requests = serialize_ollama_requests
        self._ollama_lock = RLock()

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        """Send a plain chat request to the selected backend."""
        client, resolved_model = self._resolve_backend(model)
        if client is self._ollama_client and self._serialize_ollama_requests:
            with self._ollama_lock:
                return client.chat(model=resolved_model, messages=messages)
        return client.chat(model=resolved_model, messages=messages)

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        """Send a generation request with backend-specific options."""
        client, resolved_model = self._resolve_backend(model)
        if client is self._ollama_client and self._serialize_ollama_requests:
            with self._ollama_lock:
                return client.chat_with_options(
                    model=resolved_model,
                    messages=messages,
                    options=options,
                )
        return client.chat_with_options(
            model=resolved_model,
            messages=messages,
            options=options,
        )

    def list_models(self) -> list[str]:
        """Return the merged visible model list for UI/CLI selection."""
        models: list[str] = []
        try:
            if self._serialize_ollama_requests:
                with self._ollama_lock:
                    models.extend(self._ollama_client.list_models())
            else:
                models.extend(self._ollama_client.list_models())
        except RuntimeError:
            pass
        if self._openai_client is not None:
            models.extend(
                f"{self.OPENAI_PREFIX}{name}"
                for name in self._openai_client.list_models()
            )
        seen: set[str] = set()
        merged: list[str] = []
        for item in models:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return merged

    def _resolve_backend(self, model: str):
        normalized = model.strip()
        if normalized.casefold().startswith(self.OPENAI_PREFIX):
            if self._openai_client is None:
                raise RuntimeError("OpenAI client is not available for the requested hosted model.")
            return self._openai_client, normalized[len(self.OPENAI_PREFIX) :]
        return self._ollama_client, normalized


__all__ = [
    "RoutingModelClient",
]

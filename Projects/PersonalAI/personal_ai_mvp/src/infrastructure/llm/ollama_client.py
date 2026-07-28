"""Minimal Ollama HTTP client using the local chat API."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict
from urllib import error, request

from domain.models import PromptMessage
from infrastructure.config.settings import (
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    default_ollama_fallback_base_urls,
    get_settings,
)


class OllamaClient:
    """Thin client for the local Ollama `/api/chat` endpoint."""

    DEFAULT_TIMEOUT_SECONDS = DEFAULT_OLLAMA_TIMEOUT_SECONDS

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        settings = get_settings()
        self._settings = settings
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else self.default_timeout_seconds()
        )

    @classmethod
    def default_timeout_seconds(cls) -> int:
        """Resolve the default timeout from the environment or fallback."""
        return get_settings().ollama_timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        """Sends a non-streaming chat request and returns the assistant message content."""
        return self.chat_with_options(model=model, messages=messages, options=None)

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        """Send a non-streaming chat request with optional Ollama generation options."""
        resolved_options = self._merge_default_options(model=model, options=options)
        payload = {
            "model": model,
            "stream": False,
            "messages": [asdict(message) for message in messages],
        }
        if resolved_options:
            payload["options"] = resolved_options
        raw_response = self._request_json(
            path="/api/chat",
            method="POST",
            body=json.dumps(payload).encode("utf-8"),
        )
        data = json.loads(raw_response)
        content = self._extract_message_content(data)
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        return content

    def list_models(self) -> list[str]:
        """Returns locally available Ollama model names."""
        raw_response = self._request_json(path="/api/tags", method="GET")
        data = json.loads(raw_response)
        models = data.get("models", [])
        names = [str(item.get("name", "")).strip() for item in models if item.get("name")]
        return sorted({name for name in names}, key=str.casefold)

    def _extract_message_content(self, payload: dict[str, object]) -> str:
        """Extract the best available text content from one Ollama chat response."""
        message = payload.get("message", {})
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content
        response_text = payload.get("response", "")
        if isinstance(response_text, str) and response_text.strip():
            return response_text
        thinking = message.get("thinking", "")
        if isinstance(thinking, str) and thinking.strip():
            return thinking
        return ""

    def _request_json(self, *, path: str, method: str, body: bytes | None = None) -> str:
        """Send one Ollama HTTP request, with local endpoint fallback when needed."""
        last_connection_error: error.URLError | None = None
        attempted_urls: list[str] = []

        for base_url in self._candidate_base_urls():
            attempted_urls.append(base_url)
            http_request = request.Request(
                url=f"{base_url}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
                method=method,
            )
            try:
                with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                    raw_response = response.read().decode("utf-8")
            except TimeoutError as exc:
                raise RuntimeError(self._build_timeout_message()) from exc
            except socket.timeout as exc:
                raise RuntimeError(self._build_timeout_message()) from exc
            except error.URLError as exc:
                if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                    raise RuntimeError(self._build_timeout_message()) from exc
                last_connection_error = exc
                continue

            self._base_url = base_url
            return raw_response

        if last_connection_error is None:
            raise RuntimeError(
                "Failed to reach Ollama during request execution. "
                f"Attempted base URLs: {', '.join(attempted_urls)}."
            )
        raise RuntimeError(self._build_connection_message(last_connection_error, attempted_urls))

    def _candidate_base_urls(self) -> tuple[str, ...]:
        """Return the configured Ollama URL plus sensible local fallbacks."""
        candidates: list[str] = [self._base_url]
        settings = get_settings()
        configured_fallbacks = settings.ollama_fallback_base_urls or default_ollama_fallback_base_urls(
            self._base_url
        )
        for fallback in configured_fallbacks:
            if fallback and fallback not in candidates:
                candidates.append(fallback)
        return tuple(candidates)

    def _build_timeout_message(self) -> str:
        """Return a user-facing message for slow local inference."""
        return (
            "Ollama request timed out while waiting for the model to respond. "
            f"Current timeout: {self._timeout_seconds}s. "
            "Try a smaller model or increase OLLAMA_TIMEOUT_SECONDS."
        )

    def _build_connection_message(
        self,
        exc: error.URLError,
        attempted_urls: list[str] | None = None,
    ) -> str:
        """Return a user-facing message for transport-level Ollama failures."""
        reason = exc.reason if exc.reason is not None else exc
        attempted_suffix = ""
        if attempted_urls:
            attempted_suffix = f" Attempted base URLs: {', '.join(attempted_urls)}."
        return (
            "Failed to reach Ollama during request execution. "
            f"Reason: {reason}. "
            f"Base URL: {self._base_url}."
            f"{attempted_suffix}"
        )

    def _merge_default_options(
        self,
        *,
        model: str,
        options: dict[str, object] | None,
    ) -> dict[str, object] | None:
        resolved = dict(options or {})
        if "num_ctx" not in resolved:
            default_num_ctx = self._default_num_ctx_for_model(model)
            if default_num_ctx is not None:
                resolved["num_ctx"] = default_num_ctx
        return resolved or None

    def _default_num_ctx_for_model(self, model: str) -> int | None:
        normalized = model.strip().casefold()
        for prefix, num_ctx in self._settings.ollama_num_ctx_by_model:
            if prefix.strip() and normalized.startswith(prefix.strip().casefold()):
                return num_ctx
        return None


__all__ = [
    "OllamaClient",
]

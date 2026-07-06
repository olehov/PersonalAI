"""Minimal Ollama HTTP client using the local chat API."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict
from urllib import error, request
from urllib.parse import urlsplit, urlunsplit

from personal_ai.domain.models import PromptMessage
from personal_ai.infrastructure.env_loader import load_env_file


class OllamaClient:
    """Thin client for the local Ollama `/api/chat` endpoint."""

    DEFAULT_TIMEOUT_SECONDS = 1800

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11435",
        timeout_seconds: int | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else self.default_timeout_seconds()
        )

    @classmethod
    def default_timeout_seconds(cls) -> int:
        """Resolve the default timeout from the environment or fallback."""
        load_env_file()
        raw_value = os.getenv("OLLAMA_TIMEOUT_SECONDS", "").strip()
        if not raw_value:
            return cls.DEFAULT_TIMEOUT_SECONDS
        try:
            parsed = int(raw_value)
        except ValueError:
            return cls.DEFAULT_TIMEOUT_SECONDS
        return parsed if parsed > 0 else cls.DEFAULT_TIMEOUT_SECONDS

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
        payload = {
            "model": model,
            "stream": False,
            "messages": [asdict(message) for message in messages],
        }
        if options:
            payload["options"] = options
        raw_response = self._request_json(
            path="/api/chat",
            method="POST",
            body=json.dumps(payload).encode("utf-8"),
        )
        data = json.loads(raw_response)
        message = data.get("message", {})
        content = message.get("content", "")
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
        for fallback in (
            self._replace_port(self._base_url, 11434),
            self._replace_port(self._base_url, 11435),
            "http://127.0.0.1:11434",
            "http://127.0.0.1:11435",
        ):
            if fallback and fallback not in candidates:
                candidates.append(fallback)
        return tuple(candidates)

    def _replace_port(self, base_url: str, port: int) -> str | None:
        """Return a copy of the URL with a different port, preserving scheme and host."""
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        if not hostname:
            return None
        netloc = hostname if parsed.username is None else parsed.netloc
        if ":" in hostname and not hostname.startswith("["):
            netloc = f"[{hostname}]"
        else:
            netloc = hostname
        if parsed.port == port:
            return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")
        netloc = f"{netloc}:{port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")

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

"""Minimal OpenAI Responses API client for hosted model access."""

from __future__ import annotations

import json
import socket
from dataclasses import asdict
from urllib import error, request

from domain.models import PromptMessage
from infrastructure.config.settings import get_settings


class OpenAIResponsesClient:
    """Thin client for the hosted OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int | None = None,
        configured_models: tuple[str, ...] = (),
    ) -> None:
        settings = get_settings()
        resolved_api_key = settings.openai_api_key if api_key is None else api_key
        resolved_base_url = settings.openai_base_url if base_url is None else base_url
        resolved_timeout_seconds = (
            settings.openai_timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        self._api_key = (resolved_api_key or "").strip()
        self._base_url = resolved_base_url.rstrip("/")
        self._timeout_seconds = resolved_timeout_seconds
        self._configured_models = tuple(item.strip() for item in configured_models if item.strip())

    def is_configured(self) -> bool:
        """Return whether the client has an API key configured."""
        return bool(self._api_key)

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        """Send a hosted completion request without extra generation options."""
        return self.chat_with_options(model=model, messages=messages, options=None)

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        """Send a hosted Responses API request."""
        if not self.is_configured():
            raise RuntimeError("OpenAI API key is not configured. Set OPENAI_API_KEY to use hosted GPT models.")

        payload: dict[str, object] = {
            "model": model,
            "input": [asdict(message) for message in messages],
        }
        if messages and messages[0].role == "system":
            payload["instructions"] = messages[0].content
            payload["input"] = [asdict(message) for message in messages[1:]]
        if options:
            mapped = self._map_options(options)
            payload.update(mapped)

        raw_response = self._request_json(
            path="/responses",
            method="POST",
            body=json.dumps(payload).encode("utf-8"),
        )
        data = json.loads(raw_response)
        content = self._extract_output_text(data)
        if not content:
            raise RuntimeError("OpenAI returned an empty response.")
        return content

    def list_models(self) -> list[str]:
        """Return configured hosted model names for UI selection."""
        if not self.is_configured():
            return []
        return sorted(set(self._configured_models), key=str.casefold)

    def _request_json(self, *, path: str, method: str, body: bytes | None = None) -> str:
        http_request = request.Request(
            url=f"{self._base_url}{path}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method=method,
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return response.read().decode("utf-8")
        except TimeoutError as exc:
            raise RuntimeError(self._build_timeout_message()) from exc
        except socket.timeout as exc:
            raise RuntimeError(self._build_timeout_message()) from exc
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenAI request failed with HTTP {exc.code}. Body: {body_text}"
            ) from exc
        except error.URLError as exc:
            reason = exc.reason if exc.reason is not None else exc
            raise RuntimeError(
                "Failed to reach OpenAI during request execution. "
                f"Reason: {reason}. Base URL: {self._base_url}."
            ) from exc

    def _build_timeout_message(self) -> str:
        return (
            "OpenAI request timed out while waiting for the model to respond. "
            f"Current timeout: {self._timeout_seconds}s."
        )

    def _map_options(self, options: dict[str, object]) -> dict[str, object]:
        mapped: dict[str, object] = {}
        num_predict = options.get("num_predict")
        if isinstance(num_predict, int) and num_predict > 0:
            mapped["max_output_tokens"] = num_predict
        temperature = options.get("temperature")
        if isinstance(temperature, (int, float)):
            mapped["temperature"] = temperature
        top_p = options.get("top_p")
        if isinstance(top_p, (int, float)):
            mapped["top_p"] = top_p
        return mapped

    def _extract_output_text(self, payload: dict[str, object]) -> str:
        output = payload.get("output", [])
        if not isinstance(output, list):
            return ""
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "output_text":
                    text = part.get("text", "")
                    if isinstance(text, str) and text:
                        chunks.append(text)
        return "\n".join(chunks).strip()


__all__ = [
    "OpenAIResponsesClient",
]

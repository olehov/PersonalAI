from __future__ import annotations

import threading
import time
import unittest

from domain.models import PromptMessage
from infrastructure.llm.routing_model_client import RoutingModelClient


class _FakeBackend:
    def __init__(self, *, list_models=None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._models = list_models or []

    def chat(self, *, model: str, messages: tuple[PromptMessage, ...]) -> str:
        self.calls.append(("chat", model))
        return f"chat:{model}"

    def chat_with_options(self, *, model: str, messages: tuple[PromptMessage, ...], options=None) -> str:
        self.calls.append(("chat_with_options", model))
        return f"chat_with_options:{model}"

    def list_models(self) -> list[str]:
        return list(self._models)


class RoutingModelClientTests(unittest.TestCase):
    def test_routes_openai_prefixed_models_to_openai_backend(self) -> None:
        ollama = _FakeBackend(list_models=["gemma:latest"])
        openai = _FakeBackend(list_models=["gpt-5.5"])
        client = RoutingModelClient(ollama_client=ollama, openai_client=openai)

        result = client.chat(
            model="openai:gpt-5.5",
            messages=(PromptMessage(role="user", content="Hi"),),
        )

        self.assertEqual(result, "chat:gpt-5.5")
        self.assertEqual(openai.calls, [("chat", "gpt-5.5")])
        self.assertEqual(ollama.calls, [])

    def test_routes_unprefixed_models_to_ollama_backend(self) -> None:
        ollama = _FakeBackend(list_models=["gemma:latest"])
        openai = _FakeBackend(list_models=["gpt-5.5"])
        client = RoutingModelClient(ollama_client=ollama, openai_client=openai)

        result = client.chat_with_options(
            model="gemma:latest",
            messages=(PromptMessage(role="user", content="Hi"),),
            options={"num_predict": 10},
        )

        self.assertEqual(result, "chat_with_options:gemma:latest")
        self.assertEqual(ollama.calls, [("chat_with_options", "gemma:latest")])

    def test_list_models_merges_ollama_and_prefixed_openai_entries(self) -> None:
        ollama = _FakeBackend(list_models=["gemma:latest"])
        openai = _FakeBackend(list_models=["gpt-5.5", "gpt-5-mini"])
        client = RoutingModelClient(ollama_client=ollama, openai_client=openai)

        self.assertEqual(
            client.list_models(),
            ["gemma:latest", "openai:gpt-5.5", "openai:gpt-5-mini"],
        )

    def test_serializes_ollama_requests_when_enabled(self) -> None:
        class _BlockingBackend(_FakeBackend):
            def __init__(self) -> None:
                super().__init__(list_models=["gemma:latest"])
                self.active_calls = 0
                self.max_active_calls = 0
                self._lock = threading.Lock()

            def chat(self, *, model: str, messages: tuple[PromptMessage, ...]) -> str:
                with self._lock:
                    self.active_calls += 1
                    self.max_active_calls = max(self.max_active_calls, self.active_calls)
                try:
                    time.sleep(0.05)
                    return super().chat(model=model, messages=messages)
                finally:
                    with self._lock:
                        self.active_calls -= 1

        ollama = _BlockingBackend()
        client = RoutingModelClient(ollama_client=ollama, serialize_ollama_requests=True)

        first = threading.Thread(
            target=client.chat,
            kwargs={"model": "gemma:latest", "messages": (PromptMessage(role="user", content="one"),)},
        )
        second = threading.Thread(
            target=client.chat,
            kwargs={"model": "gemma:latest", "messages": (PromptMessage(role="user", content="two"),)},
        )
        first.start()
        second.start()
        first.join()
        second.join()

        self.assertEqual(ollama.max_active_calls, 1)


if __name__ == "__main__":
    unittest.main()

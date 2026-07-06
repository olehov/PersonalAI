from __future__ import annotations

import os
import socket
import unittest
from unittest.mock import patch
from urllib import error

from personal_ai.infrastructure.ollama_client import OllamaClient


class OllamaClientTests(unittest.TestCase):
    def test_default_timeout_uses_env_override(self) -> None:
        original_value = os.environ.get("OLLAMA_TIMEOUT_SECONDS")
        try:
            os.environ["OLLAMA_TIMEOUT_SECONDS"] = "420"
            client = OllamaClient()
            self.assertEqual(client._timeout_seconds, 420)
        finally:
            if original_value is None:
                os.environ.pop("OLLAMA_TIMEOUT_SECONDS", None)
            else:
                os.environ["OLLAMA_TIMEOUT_SECONDS"] = original_value

    def test_invalid_env_timeout_falls_back_to_default(self) -> None:
        original_value = os.environ.get("OLLAMA_TIMEOUT_SECONDS")
        try:
            os.environ["OLLAMA_TIMEOUT_SECONDS"] = "bad-value"
            client = OllamaClient()
            self.assertEqual(client._timeout_seconds, OllamaClient.DEFAULT_TIMEOUT_SECONDS)
        finally:
            if original_value is None:
                os.environ.pop("OLLAMA_TIMEOUT_SECONDS", None)
            else:
                os.environ["OLLAMA_TIMEOUT_SECONDS"] = original_value

    def test_chat_timeout_surfaces_timeout_specific_message(self) -> None:
        client = OllamaClient(timeout_seconds=12)

        with patch(
            "personal_ai.infrastructure.ollama_client.request.urlopen",
            side_effect=socket.timeout("timed out"),
        ):
            with self.assertRaises(RuntimeError) as context:
                client.chat(model="gemma:latest", messages=())

        self.assertIn("timed out", str(context.exception))
        self.assertIn("12s", str(context.exception))

    def test_list_models_timeout_from_urlerror_surfaces_timeout_specific_message(self) -> None:
        client = OllamaClient(timeout_seconds=34)

        with patch(
            "personal_ai.infrastructure.ollama_client.request.urlopen",
            side_effect=error.URLError(socket.timeout("timed out")),
        ):
            with self.assertRaises(RuntimeError) as context:
                client.list_models()

        self.assertIn("timed out", str(context.exception))
        self.assertIn("34s", str(context.exception))

    def test_list_models_connection_error_surfaces_reason_and_base_url(self) -> None:
        client = OllamaClient(base_url="http://127.0.0.1:11435", timeout_seconds=34)

        with patch(
            "personal_ai.infrastructure.ollama_client.request.urlopen",
            side_effect=error.URLError(ConnectionResetError("connection reset by peer")),
        ):
            with self.assertRaises(RuntimeError) as context:
                client.list_models()

        self.assertIn("connection reset by peer", str(context.exception))
        self.assertIn("http://127.0.0.1:11435", str(context.exception))

    def test_list_models_falls_back_to_default_local_port(self) -> None:
        client = OllamaClient(base_url="http://127.0.0.1:11435", timeout_seconds=34)

        class _Response:
            def __init__(self, payload: str) -> None:
                self._payload = payload

            def read(self) -> bytes:
                return self._payload.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        def _fake_urlopen(http_request, timeout):
            if http_request.full_url == "http://127.0.0.1:11435/api/tags":
                raise error.URLError(ConnectionRefusedError("actively refused"))
            if http_request.full_url == "http://127.0.0.1:11434/api/tags":
                return _Response('{"models":[{"name":"gemma:latest"}]}')
            raise AssertionError(http_request.full_url)

        with patch(
            "personal_ai.infrastructure.ollama_client.request.urlopen",
            side_effect=_fake_urlopen,
        ):
            self.assertEqual(client.list_models(), ["gemma:latest"])

        self.assertEqual(client._base_url, "http://127.0.0.1:11434")

    def test_connection_error_reports_attempted_urls(self) -> None:
        client = OllamaClient(base_url="http://127.0.0.1:11435", timeout_seconds=34)

        with patch(
            "personal_ai.infrastructure.ollama_client.request.urlopen",
            side_effect=error.URLError(ConnectionRefusedError("actively refused")),
        ):
            with self.assertRaises(RuntimeError) as context:
                client.list_models()

        self.assertIn("actively refused", str(context.exception))
        self.assertIn("Attempted base URLs", str(context.exception))
        self.assertIn("http://127.0.0.1:11434", str(context.exception))


if __name__ == "__main__":
    unittest.main()

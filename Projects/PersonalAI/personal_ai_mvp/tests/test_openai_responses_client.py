from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from domain.models import PromptMessage
from infrastructure.llm.openai_responses_client import OpenAIResponsesClient


class OpenAIResponsesClientTests(unittest.TestCase):
    def test_list_models_returns_configured_models_only_when_key_present(self) -> None:
        client = OpenAIResponsesClient(
            api_key="test-key",
            configured_models=("gpt-5.5", "gpt-5-mini"),
        )
        self.assertEqual(client.list_models(), ["gpt-5-mini", "gpt-5.5"])

        no_key_client = OpenAIResponsesClient(
            api_key="",
            configured_models=("gpt-5.5",),
        )
        self.assertEqual(no_key_client.list_models(), [])

    def test_chat_maps_system_message_to_instructions_and_extracts_output_text(self) -> None:
        client = OpenAIResponsesClient(
            api_key="test-key",
            base_url="https://api.openai.example/v1",
        )

        class _Response:
            def read(self) -> bytes:
                return json.dumps(
                    {
                        "output": [
                            {
                                "type": "message",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": "Hosted answer.",
                                    }
                                ],
                            }
                        ]
                    }
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        captured: dict[str, object] = {}

        def _fake_urlopen(http_request, timeout):
            captured["url"] = http_request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(http_request.data.decode("utf-8"))
            return _Response()

        with patch(
            "infrastructure.llm.openai_responses_client.request.urlopen",
            side_effect=_fake_urlopen,
        ):
            text = client.chat_with_options(
                model="gpt-5.5",
                messages=(
                    PromptMessage(role="system", content="You are strict."),
                    PromptMessage(role="user", content="Hello"),
                ),
                options={"num_predict": 123},
            )

        self.assertEqual(text, "Hosted answer.")
        self.assertEqual(captured["url"], "https://api.openai.example/v1/responses")
        self.assertEqual(captured["body"]["instructions"], "You are strict.")
        self.assertEqual(captured["body"]["max_output_tokens"], 123)
        self.assertEqual(
            captured["body"]["input"],
            [{"role": "user", "content": "Hello"}],
        )


if __name__ == "__main__":
    unittest.main()

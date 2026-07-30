from __future__ import annotations

import unittest

from application.chat.preprocessor import PromptPreprocessor
from domain.models import PromptMessage


BROKEN_BSQ_PROMPT = "Р—РіРµРЅРµСЂСѓР№ РєРѕРґ РґР»СЏ bsq РЅР° C."
DOUBLE_BROKEN_BSQ_PROMPT = (
    "Р вЂ”Р С–Р ВµР Р…Р ВµРЎР‚РЎС“Р в„– "
    "Р С”Р С•Р Т‘ Р Т‘Р В»РЎРЏ bsq Р Р…Р В° C."
)


class _FakeModelClient:
    def __init__(self, response: str = "Translate this to English.") -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[PromptMessage, ...], dict[str, object] | None]] = []

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        return self.response


class _PerModelFakeClient:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, tuple[PromptMessage, ...], dict[str, object] | None]] = []

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        response = self.responses.get(model)
        if response is None:
            raise RuntimeError(f"unexpected model: {model}")
        if response.startswith("ERROR:"):
            raise RuntimeError(response.removeprefix("ERROR:"))
        return response


class _FailingModelClient:
    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        raise RuntimeError("translator unavailable")


class PromptPreprocessorTests(unittest.TestCase):
    def test_disabled_mode_returns_original_prompt(self) -> None:
        service = PromptPreprocessor(mode="disabled")

        result = service.preprocess("  Build minishell  ", workflow_hint="agent")

        self.assertEqual(result.processed_text, "Build minishell")
        self.assertEqual(result.mode, "disabled")
        self.assertFalse(result.applied)
        self.assertIsNone(result.translator_output)
        self.assertIsNone(result.translator_error)
        self.assertIsNone(result.fallback_reason)

    def test_disabled_mode_repairs_common_utf8_mojibake(self) -> None:
        service = PromptPreprocessor(mode="disabled")

        result = service.preprocess(
            f"  {DOUBLE_BROKEN_BSQ_PROMPT}  ",
            workflow_hint="ask",
        )

        self.assertEqual(result.processed_text, BROKEN_BSQ_PROMPT)
        self.assertFalse(result.applied)
        self.assertIsNone(result.translator_output)
        self.assertIsNone(result.translator_error)
        self.assertIsNone(result.fallback_reason)

    def test_translate_mode_uses_model_client_and_returns_translated_prompt(self) -> None:
        fake_client = _FakeModelClient("Generate code for bsq in C.")
        service = PromptPreprocessor(
            mode="translate_to_english",
            model_client=fake_client,
            translation_model="gemma:latest",
        )

        result = service.preprocess(DOUBLE_BROKEN_BSQ_PROMPT, workflow_hint="implementation")

        self.assertEqual(result.processed_text, "Generate code for bsq in C.")
        self.assertTrue(result.applied)
        self.assertEqual(result.translator_output, "Generate code for bsq in C.")
        self.assertIsNone(result.translator_error)
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(len(fake_client.calls), 1)
        self.assertEqual(fake_client.calls[0][0], "gemma:latest")
        self.assertEqual(fake_client.calls[0][2], {"num_predict": 220})
        self.assertIn("Workflow hint: implementation", fake_client.calls[0][1][1].content)
        self.assertIn(BROKEN_BSQ_PROMPT, fake_client.calls[0][1][1].content)
        self.assertNotIn(DOUBLE_BROKEN_BSQ_PROMPT, fake_client.calls[0][1][1].content)
        self.assertIn("You do not have access to repository files", fake_client.calls[0][1][0].content)
        self.assertNotIn("Primary Notes", fake_client.calls[0][1][1].content)
        self.assertNotIn("Related Notes", fake_client.calls[0][1][1].content)
        self.assertNotIn("chat_history", fake_client.calls[0][1][1].content)

    def test_translate_mode_falls_back_when_translation_model_is_missing(self) -> None:
        fake_client = _FakeModelClient("unused")
        service = PromptPreprocessor(
            mode="translate_to_english",
            model_client=fake_client,
            translation_model=None,
        )

        result = service.preprocess(DOUBLE_BROKEN_BSQ_PROMPT, workflow_hint="implementation")

        self.assertEqual(result.processed_text, BROKEN_BSQ_PROMPT)
        self.assertFalse(result.applied)
        self.assertIsNone(result.translator_output)
        self.assertIsNone(result.translator_error)
        self.assertEqual(result.fallback_reason, "translation_model_unavailable")
        self.assertEqual(fake_client.calls, [])

    def test_translate_mode_falls_back_when_model_call_fails(self) -> None:
        service = PromptPreprocessor(
            mode="translate_to_english",
            model_client=_FailingModelClient(),
            translation_model="gemma:latest",
        )

        result = service.preprocess(DOUBLE_BROKEN_BSQ_PROMPT, workflow_hint="implementation")

        self.assertEqual(result.processed_text, BROKEN_BSQ_PROMPT)
        self.assertFalse(result.applied)
        self.assertIsNone(result.translator_output)
        self.assertEqual(result.translator_error, "translator unavailable")
        self.assertEqual(result.fallback_reason, "translator_error")

    def test_translate_mode_falls_back_when_model_returns_blank_text(self) -> None:
        fake_client = _FakeModelClient("   ")
        service = PromptPreprocessor(
            mode="translate_to_english",
            model_client=fake_client,
            translation_model="gemma:latest",
        )

        result = service.preprocess(DOUBLE_BROKEN_BSQ_PROMPT, workflow_hint="implementation")

        self.assertEqual(result.processed_text, BROKEN_BSQ_PROMPT)
        self.assertFalse(result.applied)
        self.assertIsNone(result.translator_output)
        self.assertIsNone(result.translator_error)
        self.assertEqual(result.fallback_reason, "empty_translation_output")

    def test_translate_mode_uses_fallback_translation_model_after_primary_error(self) -> None:
        fake_client = _PerModelFakeClient(
            {
                "openai:gpt-5-mini": "ERROR:OpenAI request failed with HTTP 429.",
                "gemma:latest": "Generate full bsq implementation in C.",
            }
        )
        service = PromptPreprocessor(
            mode="translate_to_english",
            model_client=fake_client,
            translation_model="openai:gpt-5-mini",
            fallback_translation_model="gemma:latest",
        )

        result = service.preprocess(DOUBLE_BROKEN_BSQ_PROMPT, workflow_hint="implementation")

        self.assertEqual(result.processed_text, "Generate full bsq implementation in C.")
        self.assertTrue(result.applied)
        self.assertEqual(result.translator_output, "Generate full bsq implementation in C.")
        self.assertEqual(result.translator_error, "OpenAI request failed with HTTP 429.")
        self.assertEqual(result.fallback_reason, "fallback_model_applied")
        self.assertEqual([call[0] for call in fake_client.calls], ["openai:gpt-5-mini", "gemma:latest"])


if __name__ == "__main__":
    unittest.main()

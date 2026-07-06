from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from personal_ai.application.answer_service import AnswerService
from personal_ai.application.chat_service import AskComplexityError, ChatService
from personal_ai.application.knowledge_service import (
    KnowledgeService,
    serialize_generated_answer,
)
from personal_ai.application.retrieval_service import RetrievalService
from personal_ai.domain.models import PromptMessage


class FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[PromptMessage, ...]]] = []

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        self.calls.append((model, messages))
        last_message = messages[-1].content
        if "Recursive Refinement Critique:" in last_message:
            return (
                "Strengths\n- Grounded structure is present.\n\n"
                "Issues\n- Too generic.\n\n"
                "Missing Grounding\n- Needs concrete files.\n\n"
                "Improve\n- Rewrite with tighter coding detail."
            )
        if "Recursive Refinement Final Pass:" in last_message:
            return "Refined grounded answer."
        return "Grounded answer."


class FakeHistoryRepository:
    def __init__(self) -> None:
        self.saved: list[dict[str, object]] = []

    def save_generated_answer(
        self,
        answer,
        *,
        scope_dirs: tuple[str, ...] = (),
        latency_ms: int | None = None,
    ) -> None:
        self.saved.append(
            {
                "question": answer.question,
                "model": answer.model,
                "task_mode": answer.prompt.task_mode if answer.prompt is not None else "general",
                "scope_dirs": scope_dirs,
                "latency_ms": latency_ms,
            }
        )


class ChatServiceTests(unittest.TestCase):
    def test_ask_runs_grounded_prompt_through_ollama_client(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture overview.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=True,
            )

            answer = service.ask("personalai architecture", model="llama3:latest")
            payload = serialize_generated_answer(answer)

            self.assertEqual(payload["model"], "llama3:latest")
            self.assertEqual(payload["answer_text"], "Grounded answer.")
            self.assertEqual(fake_client.calls[0][0], "llama3:latest")
            self.assertEqual(fake_client.calls[0][1][0].role, "system")
            self.assertIn("code-first", fake_client.calls[0][1][0].content)
            self.assertIn("implementation help first", fake_client.calls[0][1][1].content)

    def test_ask_for_implementation_request_passes_implementation_mode_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=True,
            )

            service.ask("implement a shell parser", model="llama3:latest")

            self.assertIn("Task Mode:\nimplementation", fake_client.calls[0][1][1].content)
            self.assertIn("Response Contract:", fake_client.calls[0][1][1].content)
            self.assertIn("Code Skeleton", fake_client.calls[0][1][1].content)

    def test_ask_persists_history_when_repository_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nImplementation details.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            history_repository = FakeHistoryRepository()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                history_repository,
            )

            service.ask("implement architecture flow", model="llama3:latest", scope_dirs=("Projects",))

            self.assertEqual(len(history_repository.saved), 1)
            self.assertEqual(history_repository.saved[0]["task_mode"], "implementation")
            self.assertEqual(history_repository.saved[0]["scope_dirs"], ("Projects",))
            self.assertIsNotNone(history_repository.saved[0]["latency_ms"])

    def test_ask_includes_recent_conversation_history_before_current_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture overview.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
            )

            service.ask(
                "implement architecture flow",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="We already agreed to focus on the parser layer."),
                    PromptMessage(role="assistant", content="Next answer should continue from that parser plan."),
                ),
            )

            messages = fake_client.calls[0][1]
            self.assertEqual(messages[0].role, "system")
            self.assertEqual(messages[1].role, "user")
            self.assertIn("focus on the parser layer", messages[1].content)
            self.assertEqual(messages[2].role, "assistant")
            self.assertIn("continue from that parser plan", messages[2].content)
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Task Mode:", messages[-1].content)

    def test_ask_passes_high_reasoning_mode_into_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nImplementation details.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
            )

            service.ask(
                "compare parser designs",
                model="llama3:latest",
                reasoning_mode="high",
            )

            self.assertIn("deeper reasoning pass", fake_client.calls[0][1][0].content)
            self.assertIn("Reasoning Mode:\nhigh", fake_client.calls[0][1][-1].content)
            self.assertEqual(len(fake_client.calls), 3)
            self.assertIn("Recursive Refinement Critique:", fake_client.calls[1][1][-1].content)
            self.assertIn("Recursive Refinement Final Pass:", fake_client.calls[2][1][-1].content)

    def test_ask_uses_refined_answer_text_for_high_reasoning_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nImplementation details.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=True,
            )

            answer = service.ask(
                "compare parser designs",
                model="llama3:latest",
                reasoning_mode="high",
            )

            self.assertEqual(answer.answer_text, "Refined grounded answer.")

    def test_ask_high_reasoning_does_not_recurse_when_flag_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nImplementation details.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask(
                "compare parser designs",
                model="llama3:latest",
                reasoning_mode="high",
            )

            self.assertEqual(answer.answer_text, "Grounded answer.")
            self.assertEqual(len(fake_client.calls), 1)

    def test_chat_specific_env_flag_overrides_general_recursive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nImplementation details.\n",
                encoding="utf-8",
            )

            previous_general = os.environ.get("PERSONAL_AI_RECURSIVE_REFINEMENT")
            previous_chat = os.environ.get("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT")
            try:
                os.environ["PERSONAL_AI_RECURSIVE_REFINEMENT"] = "false"
                os.environ["PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"] = "true"

                knowledge = KnowledgeService(root)
                knowledge.load()
                fake_client = FakeOllamaClient()
                service = ChatService(
                    AnswerService(RetrievalService(knowledge)),
                    fake_client,
                )

                service.ask(
                    "compare parser designs",
                    model="llama3:latest",
                    reasoning_mode="high",
                )

                self.assertEqual(len(fake_client.calls), 3)
            finally:
                if previous_general is None:
                    os.environ.pop("PERSONAL_AI_RECURSIVE_REFINEMENT", None)
                else:
                    os.environ["PERSONAL_AI_RECURSIVE_REFINEMENT"] = previous_general
                if previous_chat is None:
                    os.environ.pop("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT", None)
                else:
                    os.environ["PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"] = previous_chat

    def test_ask_rejects_project_scale_agentic_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = FakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
            )

            heavy_prompt = """You are working inside my local project folder as an implementation agent.
Your task is to build the mandatory part of 42 minishell by actually creating and editing files in the filesystem.
Act directly in the filesystem.
Create the folders, headers, source files, and Makefile, then compile and fix errors.
Keep going until the project compiles or you hit a real blocker.
Expected workflow:
1. Inspect current directory.
2. Create project structure if needed.
3. Build after changes and fix compiler errors.
4. Run a few basic validation commands.
5. Report final status truthfully.
"""

            with self.assertRaises(AskComplexityError) as context:
                service.ask(heavy_prompt, model="deepseek-r1:8b")

            self.assertIn("full agentic project-build task", str(context.exception))
            self.assertEqual(fake_client.calls, [])


if __name__ == "__main__":
    unittest.main()

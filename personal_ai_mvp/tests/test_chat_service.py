from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from application.knowledge.answer_service import AnswerService
from application.chat.service import AskComplexityError, ChatService
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.shared.serializers import serialize_generated_answer
from domain.models import PromptMessage


class FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[PromptMessage, ...], dict[str, object] | None]] = []

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        return self.chat_with_options(model=model, messages=messages, options=None)

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            return (
                "Architecture\n- Use a parser module and execution pipeline.\n\n"
                "Modules\n- `parser.c`\n- `executor.c`\n\n"
                "Execution Flow\n1. Tokenize input.\n2. Parse commands.\n3. Execute pipeline.\n\n"
                "Edge Cases\n- Handle allocation failures.\n- Clean up opened fds.\n\n"
                "Code Skeleton\n```c\nint main(void)\n{\n    return 0;\n}\n```"
            )
        if "Recursive Refinement Critique:" in last_message:
            return (
                "Strengths\n- Grounded structure is present.\n\n"
                "Issues\n- Too generic.\n\n"
                "Missing Grounding\n- Needs concrete files.\n\n"
                "Improve\n- Rewrite with tighter coding detail."
            )
        if "Recursive Refinement Final Pass:" in last_message:
            return "Refined grounded answer."
        if "Task Mode:\nimplementation" in last_message:
            return (
                "Architecture\n- Use a parser module and execution pipeline.\n\n"
                "Modules\n- `parser.c`\n- `executor.c`\n\n"
                "Execution Flow\n1. Tokenize input.\n2. Parse commands.\n3. Execute pipeline.\n\n"
                "Edge Cases\n- Handle allocation failures.\n- Clean up opened fds.\n\n"
                "Code Skeleton\n```c\nint main(void)\n{\n    return 0;\n}\n```"
            )
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


class RepairingFakeOllamaClient(FakeOllamaClient):
    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            return (
                "Architecture\n- Repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `bsq.h`\n\n"
                "Execution Flow\n1. Read the map.\n2. Run DP.\n3. Print the square.\n\n"
                "Edge Cases\n- Empty map.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("


class RetryRepairingFakeOllamaClient(FakeOllamaClient):
    def __init__(self) -> None:
        super().__init__()
        self._repair_calls = 0

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            self._repair_calls += 1
            if self._repair_calls == 1:
                return (
                    "Architecture\n- Still partial.\n\n"
                    "Modules\n- `bsq.c`\n\n"
                    "Code Skeleton\n```c\nint solve_bsq("
                )
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("


class RefusalThenRepairFakeOllamaClient(FakeOllamaClient):
    def __init__(self) -> None:
        super().__init__()
        self._repair_calls = 0

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            self._repair_calls += 1
            if self._repair_calls == 1:
                return (
                    "I don't have enough detail about the original implementation you're trying to fix. "
                    "I need the full draft or a snippet of the previous draft before I can continue."
                )
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("


class MetaLeakThenRepairFakeOllamaClient(FakeOllamaClient):
    def __init__(self) -> None:
        super().__init__()
        self._repair_calls = 0

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            self._repair_calls += 1
            if self._repair_calls == 1:
                return (
                    "We need to finish the header and provide skeleton for main.c, utils.c, and Makefile. "
                    "Let's produce final answer with these parts."
                )
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("


class AbruptEndingThenRepairFakeOllamaClient(FakeOllamaClient):
    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return (
            "Architecture\n- Use dynamic programming.\n\n"
            "Modules\n- `bsq.c`\n- `map.c`\n\n"
            "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
            "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
            "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```\n\n"
            "Cleanup - `"
        )


class ProseOnlyThenRepairFakeOllamaClient(FakeOllamaClient):
    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return (
            "Architecture\n- Use dynamic programming with a validation pass first.\n\n"
            "Modules\n- Parser module.\n- Solver module.\n\n"
            "Execution Flow\n1. Read the map.\n2. Compute DP.\n3. Print the square.\n\n"
            "Edge Cases\n- Empty map.\n- Allocation failure.\n\n"
            "Code Skeleton\n- Main entry point.\n- Solver function.\n- Cleanup helper."
        )


class DraftAnalysisLeakThenRepairFakeOllamaClient(FakeOllamaClient):
    def __init__(self) -> None:
        super().__init__()
        self._repair_calls = 0

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        last_message = messages[-1].content
        if "Implementation Answer Repair Pass:" in last_message:
            self._repair_calls += 1
            if self._repair_calls == 1:
                return (
                    "The draft shows two separate code blocks and the parser header looks incomplete.\n"
                    "But earlier the architecture section was fine, so we mainly need to finish the remaining files."
                )
            return (
                "Architecture\n- Final repaired architecture.\n\n"
                "Modules\n- `bsq.c`\n- `map.c`\n\n"
                "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                "Code Skeleton\n```c\nint solve_bsq(void)\n{\n    return 0;\n}\n```"
            )
        return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("


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
            self.assertIn("Preferred Coverage:", fake_client.calls[0][1][1].content)
            self.assertIn("code skeleton", fake_client.calls[0][1][1].content.casefold())
            self.assertIn("do not force the whole answer into a rigid markdown document shape", fake_client.calls[0][1][1].content.casefold())
            self.assertEqual(fake_client.calls[0][2], {"num_predict": 1600})

    def test_ask_for_code_facing_question_uses_coding_mode_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Shell.md").write_text(
                "# Shell\nParser and executor design notes.\n",
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

            service.ask("explain parser cleanup flow in minishell C", model="llama3:latest")

            self.assertIn("Task Mode:\ncoding", fake_client.calls[0][1][1].content)
            self.assertIn("This request is in coding mode", fake_client.calls[0][1][1].content)

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

    def test_ask_follow_up_uses_previous_substantive_user_task_for_retrieval_and_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nImplement a dynamic-programming solution in C with a full code skeleton.\n",
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

            service.ask(
                "you did not finish the code",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\n- Use dynamic programming.\n\n"
                            "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                        ),
                    ),
                ),
            )

            messages = fake_client.calls[0][1]
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Question:\nGenerate code for bsq in C.", messages[-1].content)
            self.assertIn("Task Mode:\nimplementation", messages[-1].content)
            self.assertIn("Follow-up Recovery:", messages[-1].content)
            self.assertIn("you did not finish the code", messages[-1].content)
            self.assertIn("int **mat = malloc", messages[-1].content)
            self.assertIn("Do not ask the user to resend the previous draft", messages[-1].content)

    def test_ask_follow_up_without_partial_answer_does_not_append_recovery_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nImplement a dynamic-programming solution in C with a full code skeleton.\n",
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

            service.ask(
                "continue",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\nModules\nExecution Flow\nEdge Cases\nCode Skeleton\n"
                            "```c\nint main(void)\n{\n    return 0;\n}\n```"
                        ),
                    ),
                ),
            )

            messages = fake_client.calls[0][1]
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Question:\nGenerate code for bsq in C.", messages[-1].content)
            self.assertNotIn("Follow-up Recovery:", messages[-1].content)

    def test_ask_english_follow_up_uses_previous_task_and_recovery_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nImplement a dynamic-programming solution in C with a full code skeleton.\n",
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

            service.ask(
                "you did not finish, continue",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\n- Use dynamic programming.\n\n"
                            "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                        ),
                    ),
                ),
            )

            messages = fake_client.calls[0][1]
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Question:\nGenerate code for bsq in C.", messages[-1].content)
            self.assertIn("Follow-up Recovery:", messages[-1].content)
            self.assertIn("you did not finish, continue", messages[-1].content)
            self.assertIn("int **mat = malloc", messages[-1].content)
            self.assertIn("Do not ask the user to resend the previous draft", messages[-1].content)

    def test_ask_ukrainian_follow_up_uses_previous_task_and_recovery_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nImplement a dynamic-programming solution in C with a full code skeleton.\n",
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

            service.ask(
                "ти не завершив, допиши",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\n- Use dynamic programming.\n\n"
                            "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                        ),
                    ),
                ),
            )

            messages = fake_client.calls[0][1]
            self.assertEqual(messages[-1].role, "user")
            self.assertIn("Question:\nGenerate code for bsq in C.", messages[-1].content)
            self.assertIn("Follow-up Recovery:", messages[-1].content)
            self.assertIn("ти не завершив, допиши", messages[-1].content)
            self.assertIn("int **mat = malloc", messages[-1].content)

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
            self.assertEqual(fake_client.calls[0][2], {"num_predict": 900})
            self.assertEqual(fake_client.calls[1][2], {"num_predict": 220})
            self.assertEqual(fake_client.calls[2][2], {"num_predict": 900})

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

    def test_ask_repairs_incomplete_implementation_answer_before_returning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = RepairingFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask("generate code for bsq in C", model="llama3:latest")

            self.assertEqual(len(fake_client.calls), 2)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn("A fenced code block is left open.", fake_client.calls[1][1][-1].content)
            self.assertIn("Missing sections: Modules, Execution Flow, Edge Cases.", fake_client.calls[1][1][-1].content)
            self.assertIn("Code Skeleton", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_ask_retries_repair_when_first_repair_is_still_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = RetryRepairingFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask("generate code for bsq in C", model="llama3:latest")

            self.assertEqual(len(fake_client.calls), 3)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[2][1][-1].content)
            self.assertEqual(fake_client.calls[1][2], {"num_predict": 1400})
            self.assertEqual(fake_client.calls[2][2], {"num_predict": 2000})
            self.assertIn("Execution Flow", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_follow_up_repair_retries_when_model_claims_draft_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = RefusalThenRepairFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask(
                "you did not finish, complete everything and do not restart from scratch",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\n- Use dynamic programming.\n\n"
                            "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                        ),
                    ),
                ),
            )

            self.assertEqual(len(fake_client.calls), 3)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn(
                "The answer incorrectly claims that the previous draft or task context is missing",
                fake_client.calls[2][1][-1].content,
            )
            self.assertIn("Execution Flow", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_follow_up_repair_retries_when_model_leaks_internal_repair_commentary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = MetaLeakThenRepairFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask(
                "you did not finish, complete everything and do not restart from scratch",
                model="llama3:latest",
                conversation_history=(
                    PromptMessage(role="user", content="Generate code for bsq in C."),
                    PromptMessage(
                        role="assistant",
                        content=(
                            "Architecture\n- Use dynamic programming.\n\n"
                            "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                        ),
                    ),
                ),
            )

            self.assertEqual(len(fake_client.calls), 3)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn(
                "The answer leaked internal repair or planning commentary",
                fake_client.calls[2][1][-1].content,
            )
            self.assertIn("Execution Flow", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_ask_repairs_abruptly_truncated_implementation_tail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = AbruptEndingThenRepairFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask("generate code for bsq in C", model="llama3:latest")

            self.assertEqual(len(fake_client.calls), 2)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn("Inline or fenced code is left open.", fake_client.calls[1][1][-1].content)
            self.assertIn(
                "The answer appears to stop abruptly before finishing the current section.",
                fake_client.calls[1][1][-1].content,
            )
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_ask_repairs_prose_only_implementation_answer_when_code_was_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = ProseOnlyThenRepairFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask("generate code for bsq in C", model="llama3:latest")

            self.assertEqual(len(fake_client.calls), 2)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn(
                "The request explicitly asked for code generation, but the answer does not include concrete code or a file-by-file skeleton.",
                fake_client.calls[1][1][-1].content,
            )
            self.assertIn("```c", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_ask_retries_repair_when_model_returns_draft_analysis_instead_of_final_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            fake_client = DraftAnalysisLeakThenRepairFakeOllamaClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=False,
            )

            answer = service.ask("generate code for bsq in C", model="llama3:latest")

            self.assertEqual(len(fake_client.calls), 3)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[1][1][-1].content)
            self.assertIn(
                "The answer starts with internal repair or review commentary instead of the final implementation answer.",
                fake_client.calls[2][1][-1].content,
            )
            self.assertIn("Execution Flow", answer.answer_text)
            self.assertIn("int solve_bsq(void)", answer.answer_text)

    def test_high_reasoning_implementation_answer_can_trigger_repair_after_refinement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()

            class HighReasoningRepairClient(FakeOllamaClient):
                def chat_with_options(
                    self,
                    *,
                    model: str,
                    messages: tuple[PromptMessage, ...],
                    options: dict[str, object] | None = None,
                ) -> str:
                    self.calls.append((model, messages, options))
                    last_message = messages[-1].content
                    if "Recursive Refinement Critique:" in last_message:
                        return "Strengths\n- Some structure.\n\nIssues\n- Incomplete.\n\nMissing Grounding\n- Missing modules.\n\nImprove\n- Finish it."
                    if "Recursive Refinement Final Pass:" in last_message:
                        return "Architecture\n- Still incomplete.\n\nCode Skeleton\n```c\nint main("
                    if "Implementation Answer Repair Pass:" in last_message:
                        return (
                            "Architecture\n- Final repaired architecture.\n\n"
                            "Modules\n- `bsq.c`\n- `map.c`\n\n"
                            "Execution Flow\n1. Parse.\n2. Solve.\n3. Print.\n\n"
                            "Edge Cases\n- Invalid rows.\n- Allocation failure.\n\n"
                            "Code Skeleton\n```c\nint main(void)\n{\n    return 0;\n}\n```"
                        )
                    return "Architecture\n- Draft.\n\nCode Skeleton\n```c\nint main("

            fake_client = HighReasoningRepairClient()
            service = ChatService(
                AnswerService(RetrievalService(knowledge)),
                fake_client,
                recursive_refinement_enabled=True,
            )

            answer = service.ask(
                "generate code for bsq in C",
                model="llama3:latest",
                reasoning_mode="high",
            )

            self.assertEqual(len(fake_client.calls), 4)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[3][1][-1].content)
            self.assertIn("int main(void)", answer.answer_text)

    def test_ask_uses_larger_generation_cap_for_resource_heavy_gpt_oss_implementation_answers(self) -> None:
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
                recursive_refinement_enabled=False,
            )

            service.ask("implement bsq in C", model="gpt-oss:20b")

            self.assertEqual(fake_client.calls[0][2], {"num_predict": 1400})

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

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from personal_ai.domain.models import PromptMessage
from tests.agent_runtime_test_support import AgentRuntimeServiceTestSupport


class AgentRuntimeReasoningTests(AgentRuntimeServiceTestSupport):
    def test_run_can_split_planner_and_executor_models_via_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()
            (root / "Projects" / "Minishell" / "src").mkdir(parents=True)
            (root / "Projects" / "Minishell" / "include").mkdir(parents=True)
            (root / "Projects" / "Minishell" / "Makefile").write_text(
                "all:\n\tcc src/main.c\n",
                encoding="utf-8",
            )

            previous_planner = os.environ.get("PERSONAL_AI_AGENT_PLANNER_MODEL")
            previous_executor = os.environ.get("PERSONAL_AI_AGENT_EXECUTOR_MODEL")
            try:
                os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = "deepseek-r1:8b"
                os.environ["PERSONAL_AI_AGENT_EXECUTOR_MODEL"] = "qwen2.5-coder:7b"

                fake_client, service = self._build_service(
                    root,
                    recursive_refinement_enabled=True,
                )

                payload = self._run_payload(
                    service,
                    "Build the mandatory part of minishell.",
                    model="gemma:latest",
                    reasoning_mode="high",
                )

                self.assertEqual(payload["model"], "deepseek-r1:8b")
                self.assertEqual(payload["executor_model"], "qwen2.5-coder:7b")
                self.assertEqual(fake_client.calls[0][0], "deepseek-r1:8b")
                self.assertEqual(fake_client.calls[1][0], "deepseek-r1:8b")
                self.assertEqual(fake_client.calls[2][0], "deepseek-r1:8b")
                module_draft_call = next(
                    model_name
                    for model_name, messages, _ in fake_client.calls
                    if "Module Draft Contract:" in messages[-1].content
                )
                patch_plan_call = next(
                    model_name
                    for model_name, messages, _ in fake_client.calls
                    if "Patch Planning Contract:" in messages[-1].content
                )
                self.assertEqual(module_draft_call, "qwen2.5-coder:7b")
                self.assertEqual(patch_plan_call, "qwen2.5-coder:7b")
            finally:
                if previous_planner is None:
                    os.environ.pop("PERSONAL_AI_AGENT_PLANNER_MODEL", None)
                else:
                    os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = previous_planner
                if previous_executor is None:
                    os.environ.pop("PERSONAL_AI_AGENT_EXECUTOR_MODEL", None)
                else:
                    os.environ["PERSONAL_AI_AGENT_EXECUTOR_MODEL"] = previous_executor

    def test_run_includes_recent_conversation_history_in_planning_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            fake_client, service = self._build_service(root)

            service.run(
                "Build the mandatory part of minishell.",
                model="deepseek-r1:8b",
                conversation_history=(
                    PromptMessage(role="user", content="Previously we decided to start with parsing."),
                    PromptMessage(role="assistant", content="Keep the next slice narrow and parser-first."),
                ),
            )

            planning_messages = fake_client.calls[0][1]
            self.assertEqual(planning_messages[0].role, "system")
            self.assertEqual(planning_messages[1].role, "user")
            self.assertIn("start with parsing", planning_messages[1].content)
            self.assertEqual(planning_messages[2].role, "assistant")
            self.assertIn("parser-first", planning_messages[2].content)
            self.assertEqual(planning_messages[-1].role, "user")
            self.assertIn("Agent Runtime Contract:", planning_messages[-1].content)

    def test_run_supports_high_reasoning_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            fake_client, service = self._build_service(root)

            service.run(
                "Build the mandatory part of minishell.",
                model="gemma:latest",
                reasoning_mode="high",
            )

            self.assertIn("High reasoning mode is enabled", fake_client.calls[0][1][0].content)
            self.assertIn("Reasoning Mode:\nhigh", fake_client.calls[0][1][-1].content)
            self.assertIn("Recursive Planning Critique:", fake_client.calls[1][1][-1].content)
            self.assertIn("Recursive Planning Final Pass:", fake_client.calls[2][1][-1].content)

    def test_run_uses_refined_planning_output_for_high_reasoning_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            fake_client, service = self._build_service(
                root,
                recursive_refinement_enabled=True,
            )

            artifact = service.run(
                "Build the mandatory part of minishell.",
                model="gemma:latest",
                reasoning_mode="high",
            )

            self.assertIn("Refined goal.", artifact.final_output)

    def test_run_high_reasoning_does_not_recurse_when_flag_is_disabled(self) -> None:
        previous_discussion = os.environ.get("PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            try:
                os.environ["PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"] = "false"
                fake_client, service = self._build_service(
                    root,
                    recursive_refinement_enabled=False,
                )

                artifact = service.run(
                    "Build the mandatory part of minishell.",
                    model="deepseek-r1:8b",
                    reasoning_mode="high",
                )

                self.assertEqual(
                    artifact.final_output,
                    "Goal\nConstraints\nExisting Context\nModules\nIncremental Slices\n"
                    "First Slice\nFirst Actions\nValidation\nRuntime Limits",
                )
                self.assertFalse(
                    any(
                        "Recursive Planning Critique:" in messages[-1].content
                        or "Recursive Planning Final Pass:" in messages[-1].content
                        for _, messages, _ in fake_client.calls
                    )
                )
            finally:
                if previous_discussion is None:
                    os.environ.pop("PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION", None)
                else:
                    os.environ["PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"] = previous_discussion

    def test_agent_specific_env_flag_overrides_general_recursive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            previous_general = os.environ.get("PERSONAL_AI_RECURSIVE_REFINEMENT")
            previous_agent = os.environ.get("PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT")
            try:
                os.environ["PERSONAL_AI_RECURSIVE_REFINEMENT"] = "false"
                os.environ["PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT"] = "true"

                fake_client, service = self._build_service(root)

                service.run(
                    "Build the mandatory part of minishell.",
                    model="gemma:latest",
                    reasoning_mode="high",
                )

                self.assertTrue(
                    any(
                        "Recursive Planning Critique:" in messages[-1].content
                        for _, messages, _ in fake_client.calls
                    )
                )
            finally:
                if previous_general is None:
                    os.environ.pop("PERSONAL_AI_RECURSIVE_REFINEMENT", None)
                else:
                    os.environ["PERSONAL_AI_RECURSIVE_REFINEMENT"] = previous_general
                if previous_agent is None:
                    os.environ.pop("PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT", None)
                else:
                    os.environ["PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT"] = previous_agent

    def test_run_keeps_recursive_planning_for_deepseek_models_with_bounded_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            fake_client, service = self._build_service(
                root,
                recursive_refinement_enabled=True,
            )

            service.run(
                "Build the mandatory part of minishell.",
                model="deepseek-r1:8b",
                reasoning_mode="high",
            )

            self.assertTrue(
                any(
                    "Recursive Planning Critique:" in messages[-1].content
                    for _, messages, _ in fake_client.calls
                )
            )
            self.assertEqual(fake_client.calls[0][2], {"num_predict": 520})
            self.assertEqual(fake_client.calls[1][2], {"num_predict": 180})
            self.assertEqual(fake_client.calls[2][2], {"num_predict": 520})

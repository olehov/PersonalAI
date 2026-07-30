from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.cli_test_support import CliTestSupport
from tests.path_test_support import history_db_path


class CliTests(CliTestSupport):

    def test_scan_outputs_summary_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "One.md").write_text("# One\nSee [[Two]].\n", encoding="utf-8")
            (root / "Two.md").write_text("---\ntype: example\n---\n# Two\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                ["--vault", str(root), "--format", "json", "scan"]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["note_count"], 2)
            self.assertEqual(payload["notes_with_metadata"], 1)
            self.assertEqual(payload["notes_with_links"], 1)

    def test_related_outputs_linked_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text("# Architecture\n[[Vision]]\n", encoding="utf-8")
            (root / "Vision.md").write_text("# Vision\n", encoding="utf-8")

            exit_code, stdout = self._run_cli(["--vault", str(root), "related", "Architecture"])
            self.assertEqual(exit_code, 0)
            self.assertIn("Vision.md | Vision", stdout)

    def test_show_outputs_json_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Vision.md").write_text("---\ntype: note\n---\n# Vision\n[[Roadmap]]\n", encoding="utf-8")
            (root / "Roadmap.md").write_text("# Roadmap\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                ["--vault", str(root), "--format", "json", "show", "Vision"]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["title"], "Vision")
            self.assertEqual(payload["metadata"]["values"]["type"], "note")
            self.assertEqual(payload["links"][0]["target"], "Roadmap")

    def test_show_returns_non_zero_for_missing_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Vision.md").write_text("# Vision\n", encoding="utf-8")

            exit_code, stdout = self._run_cli(["--vault", str(root), "show", "Missing"])
            self.assertEqual(exit_code, 1)
            self.assertIn("Note not found", stdout)

    def test_retrieve_outputs_json_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture.\n[[Vision]]\n",
                encoding="utf-8",
            )
            (root / "Vision.md").write_text("# Vision\nProduct direction.\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "retrieve",
                    "personalai architecture",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["primary_notes"][0]["note"]["title"], "Architecture")
            selected_titles = {
                item["note"]["title"] for item in payload["primary_notes"] + payload["related_notes"]
            }
            self.assertIn("Vision", selected_titles)

    def test_answer_outputs_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture.\n[[Vision]]\n",
                encoding="utf-8",
            )
            (root / "Vision.md").write_text("# Vision\nProduct direction.\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "answer",
                    "how does personalai architecture work",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["messages"][0]["role"], "system")
            self.assertEqual(payload["task_mode"], "general")
            self.assertIn("Architecture.md", payload["citations"])

    def test_answer_marks_implementation_mode_for_build_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and execution flow.\n",
                encoding="utf-8",
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "answer",
                    "implement minishell parser",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task_mode"], "implementation")
            self.assertIn("Task Mode:\nimplementation", payload["messages"][1]["content"])

    def test_ask_outputs_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture.\n",
                encoding="utf-8",
            )

            with patch(
                "application.chat.service.ChatService.ask",
                return_value=type(
                    "Generated",
                    (),
                    {
                        "model": "llama3:latest",
                        "question": "personalai architecture",
                        "answer_text": "Grounded answer.",
                        "citations": ("Architecture.md",),
                        "prompt": None,
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "ask",
                        "personalai architecture",
                        "--model",
                        "llama3:latest",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["model"], "llama3:latest")
            self.assertEqual(payload["answer_text"], "Grounded answer.")

    def test_agent_runtime_outputs_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            with patch(
                "application.agent_runtime.service.AgentRuntimeService.run",
                return_value=type(
                    "Artifact",
                    (),
                    {
                        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
                        "model": "deepseek-r1:8b",
                        "request_text": "build minishell",
                        "normalized_goal": "build minishell",
                        "task_mode": "implementation",
                        "status": "needs_execution_layer",
                        "scope_dirs": ("Projects",),
                        "citations": ("Projects/Minishell.md",),
                        "steps": (
                            type(
                                "Step",
                                (),
                                {
                                    "step_index": 1,
                                    "kind": "retrieval",
                                    "title": "Grounded Retrieval",
                                    "input_text": "build minishell",
                                    "output_text": "question=build minishell",
                                    "observation": "Retrieved 1 primary notes and 0 related notes.",
                                },
                            )(),
                        ),
                        "recommended_actions": (
                            type(
                                "Action",
                                (),
                                {
                                    "action_type": "inspect_note",
                                    "title": "Inspect Primary Knowledge Note",
                                    "target": "Projects/Minishell.md",
                                    "instruction": "Read the highest-priority grounded note.",
                                    "rationale": "Ground execution in vault context.",
                                },
                            )(),
                        ),
                        "action_executions": (
                            type(
                                "Execution",
                                (),
                                {
                                    "action_type": "inspect_note",
                                    "target": "Projects/Minishell.md",
                                    "status": "executed",
                                    "output_text": "title=Minishell",
                                },
                            )(),
                        ),
                        "final_output": "Goal\nConstraints\nModules\nFirst Slice",
                        "prompt": None,
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "agent-runtime",
                        "build minishell",
                        "--model",
                        "deepseek-r1:8b",
                        "--scope-dir",
                        "Projects",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["model"], "deepseek-r1:8b")
            self.assertEqual(payload["status"], "needs_execution_layer")
            self.assertEqual(payload["steps"][0]["kind"], "retrieval")
            self.assertEqual(payload["scope_dirs"], ["Projects"])
            self.assertEqual(payload["recommended_actions"][0]["action_type"], "inspect_note")
            self.assertEqual(payload["action_executions"][0]["status"], "executed")
            self.assertEqual(payload["overview"]["step_count"], 1)
            self.assertEqual(payload["overview"]["recommended_action_count"], 1)
            self.assertEqual(payload["overview"]["executed_action_count"], 1)

    def test_agent_runtime_text_output_is_grouped_by_timeline_and_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            with patch(
                "application.agent_runtime.service.AgentRuntimeService.run",
                return_value=type(
                    "Artifact",
                    (),
                    {
                        "generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC),
                        "model": "deepseek-r1:8b",
                        "request_text": "build minishell",
                        "normalized_goal": "build minishell",
                        "task_mode": "implementation",
                        "status": "needs_execution_layer",
                        "scope_dirs": ("Projects",),
                        "citations": ("Projects/Minishell.md",),
                        "steps": (
                            type(
                                "Step",
                                (),
                                {
                                    "step_index": 1,
                                    "kind": "retrieval",
                                    "title": "Grounded Retrieval",
                                    "input_text": "build minishell",
                                    "output_text": "question=build minishell",
                                    "observation": "Retrieved 1 primary note.",
                                },
                            )(),
                        ),
                        "recommended_actions": (
                            type(
                                "Action",
                                (),
                                {
                                    "action_type": "inspect_note",
                                    "title": "Inspect Primary Knowledge Note",
                                    "target": "Projects/Minishell.md",
                                    "instruction": "Read the highest-priority grounded note.",
                                    "rationale": "Ground execution in vault context.",
                                },
                            )(),
                        ),
                        "action_executions": (
                            type(
                                "Execution",
                                (),
                                {
                                    "action_type": "inspect_note",
                                    "target": "Projects/Minishell.md",
                                    "status": "executed",
                                    "output_text": "title=Minishell",
                                },
                            )(),
                        ),
                        "final_output": "Goal\nConstraints\nModules\nFirst Slice",
                        "prompt": None,
                    },
                )(),
            ):
                exit_code, rendered = self._run_cli(
                    [
                        "--vault",
                        str(root),
                        "agent-runtime",
                        "build minishell",
                        "--model",
                        "deepseek-r1:8b",
                        "--scope-dir",
                        "Projects",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("overview: steps=1", rendered)
            self.assertIn("timeline:", rendered)
            self.assertIn("recommended_actions:", rendered)
            self.assertIn("action_executions:", rendered)

    def test_ask_persists_history_and_history_command_reads_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_db = history_db_path(root)
            (root / "Projects").mkdir()
            (root / "Projects" / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            with patch(
                "infrastructure.llm.ollama_client.OllamaClient.chat",
                return_value="Architecture\nModules\nExecution Flow\nEdge Cases\nCode Skeleton",
            ):
                ask_exit_code, _ = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--history-db",
                        str(history_db),
                        "--format",
                        "json",
                        "ask",
                        "implement shell parser",
                        "--model",
                        "gemma:latest",
                    ]
                )

            self.assertEqual(ask_exit_code, 0)

            history_exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--history-db",
                    str(history_db),
                    "--format",
                    "json",
                    "history",
                    "--limit",
                    "5",
                ]
            )
            self.assertEqual(history_exit_code, 0)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["model"], "gemma:latest")
            self.assertEqual(payload[0]["task_mode"], "implementation")
            self.assertEqual(payload[0]["question"], "implement shell parser")

    def test_agent_history_reads_persisted_agent_runtime_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_db = history_db_path(root)

            from infrastructure.history.repository import SQLiteQueryHistoryRepository
            from domain.models import AgentRuntimeArtifact

            repository = SQLiteQueryHistoryRepository(history_db)
            repository.save_agent_runtime_artifact(
                AgentRuntimeArtifact(
                    model="deepseek-r1:8b",
                    request_text="build minishell",
                    normalized_goal="build minishell",
                    task_mode="implementation",
                    status="needs_execution_layer",
                    scope_dirs=("Projects",),
                    citations=("Projects/Minishell.md",),
                    steps=(),
                    final_output="Goal\nConstraints",
                ),
                latency_ms=51,
            )

            history_exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--history-db",
                    str(history_db),
                    "--format",
                    "json",
                    "agent-history",
                    "--limit",
                    "5",
                ]
            )
            self.assertEqual(history_exit_code, 0)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["model"], "deepseek-r1:8b")
            self.assertEqual(payload[0]["status"], "needs_execution_layer")


if __name__ == "__main__":
    unittest.main()

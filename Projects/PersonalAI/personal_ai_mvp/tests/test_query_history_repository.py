from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_ai.application.answer_service import AnswerService
from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.retrieval_service import RetrievalService
from personal_ai.domain.models import (
    AgentRuntimeArtifact,
    AgentRuntimeDiscussionTrace,
    AgentRuntimeStep,
    AgentRuntimeTaskPlan,
    AgentRuntimeTaskPlanEntry,
    GeneratedAnswer,
)
from personal_ai.infrastructure.query_history_repository import SQLiteQueryHistoryRepository
from personal_ai.application.benchmark_run_service import BenchmarkRunResult


class QueryHistoryRepositoryTests(unittest.TestCase):
    def test_save_and_list_generated_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            (root / "Shell.md").write_text(
                "# Shell\nImplement parser and executor.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            prompt = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "implement shell parser"
            )
            repository = SQLiteQueryHistoryRepository(database_path)

            repository.save_generated_answer(
                GeneratedAnswer(
                    model="gemma:latest",
                    question="implement shell parser",
                    answer_text="Architecture\n...\nCode Skeleton\n...",
                    citations=prompt.citations,
                    prompt=prompt,
                ),
                scope_dirs=("Projects",),
                latency_ms=123,
            )

            entries = repository.list_entries(limit=5)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].model, "gemma:latest")
            self.assertEqual(entries[0].task_mode, "implementation")
            self.assertEqual(entries[0].scope_dirs, ("Projects",))
            self.assertEqual(entries[0].latency_ms, 123)
            self.assertIsNotNone(entries[0].prompt_payload)
            note_payload = entries[0].prompt_payload["retrieval"]["primary_notes"][0]["note"]
            self.assertIn("excerpt", note_payload)
            self.assertIn("content_length", note_payload)
            self.assertNotIn("content", note_payload)
            self.assertGreater(note_payload["content_length"], 0)
            self.assertLessEqual(
                len(entries[0].prompt_payload["messages"]),
                8,
            )

    def test_save_and_list_agent_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(database_path)

            artifact = AgentRuntimeArtifact(
                model="deepseek-r1:8b",
                request_text="build minishell",
                normalized_goal="build minishell",
                task_mode="implementation",
                status="needs_execution_layer",
                scope_dirs=("Projects",),
                citations=("Projects/Minishell.md",),
                steps=(
                    AgentRuntimeStep(
                        step_index=1,
                        kind="retrieval",
                        title="Grounded Retrieval",
                        input_text="build minishell",
                        output_text="question=build minishell",
                        observation="Retrieved 1 primary note.",
                    ),
                ),
                final_output="Goal\nConstraints\nModules\nFirst Slice",
            )

            repository.save_agent_runtime_artifact(
                artifact,
                latency_ms=88,
            )

            entries = repository.list_agent_runs(limit=5)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].model, "deepseek-r1:8b")
            self.assertEqual(entries[0].task_mode, "implementation")
            self.assertEqual(entries[0].status, "needs_execution_layer")
            self.assertEqual(entries[0].scope_dirs, ("Projects",))
            self.assertEqual(entries[0].latency_ms, 88)
            self.assertIsNotNone(entries[0].artifact_payload)
            self.assertIsNone(entries[0].artifact_payload["prompt"])

    def test_agent_runtime_artifact_history_uses_compact_prompt_note_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            prompt = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "implement shell parser"
            )
            repository = SQLiteQueryHistoryRepository(database_path)

            artifact = AgentRuntimeArtifact(
                model="deepseek-r1:8b",
                request_text="build minishell",
                normalized_goal="build minishell",
                task_mode="implementation",
                status="needs_execution_layer",
                scope_dirs=("Projects",),
                citations=("Projects/Minishell.md",),
                steps=(
                    AgentRuntimeStep(
                        step_index=1,
                        kind="retrieval",
                        title="Grounded Retrieval",
                        input_text="build minishell",
                        output_text="question=build minishell",
                        observation="Retrieved 1 primary note.",
                    ),
                ),
                final_output="Goal\nConstraints\nModules\nFirst Slice",
                prompt=prompt,
            )

            repository.save_agent_runtime_artifact(artifact, latency_ms=88)

            entries = repository.list_agent_runs(limit=5)

            note_payload = entries[0].artifact_payload["prompt"]["retrieval"]["primary_notes"][0]["note"]
            self.assertIn("excerpt", note_payload)
            self.assertIn("content_length", note_payload)
            self.assertNotIn("content", note_payload)

    def test_update_agent_runtime_task_plan_persists_artifact_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(database_path)

            artifact = AgentRuntimeArtifact(
                model="deepseek-r1:8b",
                request_text="build minishell",
                normalized_goal="build minishell",
                task_mode="implementation",
                status="needs_execution_layer",
                task_plan=AgentRuntimeTaskPlan(
                    goal="build minishell",
                    current_focus="Parser stub",
                    summary="1 planned implementation task.",
                    entries=(
                        AgentRuntimeTaskPlanEntry(
                            step_index=1,
                            title="Parser stub",
                            status="next",
                            details="Add parser entrypoint.",
                            source_section="Incremental Slices",
                        ),
                    ),
                    validation_checks=("make all",),
                ),
                final_output="Goal\nConstraints\nFirst Slice",
            )

            saved = repository.save_agent_runtime_artifact(artifact, latency_ms=88)
            updated = repository.update_agent_runtime_task_plan(
                entry_id=saved.entry_id,
                task_plan_payload={
                    "goal": "build minishell",
                    "current_focus": "Tokenizer wiring",
                    "summary": "2 planned implementation tasks. 1 completed, 1 remaining.",
                    "entries": [
                        {
                            "step_index": 1,
                            "title": "Parser stub",
                            "status": "completed",
                            "details": "Add parser entrypoint.",
                            "source_section": "Incremental Slices",
                        },
                        {
                            "step_index": 2,
                            "title": "Tokenizer wiring",
                            "status": "next",
                            "details": "Connect parser to tokenizer output.",
                            "source_section": "Incremental Slices",
                        },
                    ],
                    "validation_checks": ["make all"],
                },
            )

            self.assertIsNotNone(updated)
            self.assertEqual(
                updated.artifact_payload["task_plan"]["entries"][0]["status"],
                "completed",
            )
            self.assertEqual(
                updated.artifact_payload["task_plan"]["current_focus"],
                "Tokenizer wiring",
            )

    def test_save_and_list_benchmark_run_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(database_path)

            repository.save_benchmark_run_result(
                BenchmarkRunResult(
                    pack_id="repo-aware-v1",
                    task_id="execution-honesty-minishell-build",
                    category="execution_honesty",
                    workflow="agent",
                    model="deepseek-r1:8b",
                    status="needs_execution_layer",
                    scope_dirs=("Projects",),
                    prompt_text="Build the mandatory part of minishell.",
                    latency_ms=144,
                    result_payload={"status": "needs_execution_layer", "final_output": "Goal"},
                )
            )

            entries = repository.list_benchmark_runs(limit=5)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].pack_id, "repo-aware-v1")
            self.assertEqual(entries[0].task_id, "execution-honesty-minishell-build")
            self.assertEqual(entries[0].workflow, "agent")
            self.assertEqual(entries[0].latency_ms, 144)
            self.assertEqual(entries[0].result_payload["status"], "needs_execution_layer")

    def test_generated_answer_history_prunes_old_entries_beyond_retention_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            (root / "Shell.md").write_text(
                "# Shell\nImplement parser and executor.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            prompt = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "implement shell parser"
            )
            repository = SQLiteQueryHistoryRepository(
                database_path,
                query_history_retention=2,
            )

            for index in range(3):
                repository.save_generated_answer(
                    GeneratedAnswer(
                        model="gemma:latest",
                        question=f"implement shell parser {index}",
                        answer_text="Architecture\n...\nCode Skeleton\n...",
                        citations=prompt.citations,
                        prompt=prompt,
                    ),
                )

            entries = repository.list_entries(limit=10)

            self.assertEqual(repository.count_entries(), 2)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].question, "implement shell parser 2")
            self.assertEqual(entries[1].question, "implement shell parser 1")

    def test_agent_runtime_history_prunes_old_entries_beyond_retention_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(
                database_path,
                agent_run_history_retention=2,
            )

            for index in range(3):
                repository.save_agent_runtime_artifact(
                    AgentRuntimeArtifact(
                        model="deepseek-r1:8b",
                        request_text=f"build minishell {index}",
                        normalized_goal=f"build minishell {index}",
                        task_mode="implementation",
                        status="needs_execution_layer",
                        final_output="Goal\nConstraints\nModules\nFirst Slice",
                    )
                )

            entries = repository.list_agent_runs(limit=10)

            self.assertEqual(repository.count_agent_runs(), 2)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].request_text, "build minishell 2")
            self.assertEqual(entries[1].request_text, "build minishell 1")

    def test_agent_runtime_history_compacts_large_artifact_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(database_path)

            long_text = "x" * 5000
            artifact = AgentRuntimeArtifact(
                model="deepseek-r1:8b",
                request_text="build minishell",
                normalized_goal="build minishell",
                task_mode="implementation",
                status="needs_execution_layer",
                steps=(
                    AgentRuntimeStep(
                        step_index=1,
                        kind="planning",
                        title="Plan",
                        input_text=long_text,
                        output_text=long_text,
                        observation=long_text,
                    ),
                ),
                final_output=long_text,
            )

            repository.save_agent_runtime_artifact(artifact)
            entries = repository.list_agent_runs(limit=1)
            payload = entries[0].artifact_payload

            self.assertTrue(payload["steps"][0]["input_text"].endswith("..."))
            self.assertTrue(payload["steps"][0]["output_text"].endswith("..."))
            self.assertTrue(payload["steps"][0]["observation"].endswith("..."))
            self.assertTrue(payload["final_output"].endswith("..."))
            self.assertLess(len(payload["final_output"]), len(long_text))

    def test_agent_runtime_history_persists_discussion_trace_and_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database_path = root / ".personal_ai" / "query_history.sqlite3"
            repository = SQLiteQueryHistoryRepository(database_path)

            artifact = AgentRuntimeArtifact(
                model="gemma3:4b",
                executor_model="qwen2.5-coder:7b",
                critic_model="gemma:latest",
                synthesis_model="deepseek-r1:8b",
                discussion_preset="coder_critic",
                discussion_trace=AgentRuntimeDiscussionTrace(
                    preset="coder_critic",
                    planner_draft="Planner draft " * 80,
                    critic_feedback="Critic feedback " * 80,
                    synthesis_output="Synthesis output " * 80,
                    fallback_used="self_refinement_after_synthesis_failure",
                ),
                request_text="build minishell",
                normalized_goal="build minishell",
                task_mode="implementation",
                status="needs_execution_layer",
                final_output="Goal\nConstraints\nModules\nFirst Slice",
            )

            repository.save_agent_runtime_artifact(artifact)
            entries = repository.list_agent_runs(limit=1)
            payload = entries[0].artifact_payload

            self.assertEqual(payload["executor_model"], "qwen2.5-coder:7b")
            self.assertEqual(payload["critic_model"], "gemma:latest")
            self.assertEqual(payload["synthesis_model"], "deepseek-r1:8b")
            self.assertEqual(payload["discussion_preset"], "coder_critic")
            self.assertEqual(payload["discussion_trace"]["preset"], "coder_critic")
            self.assertEqual(
                payload["discussion_trace"]["fallback_used"],
                "self_refinement_after_synthesis_failure",
            )
            self.assertTrue(payload["discussion_trace"]["planner_draft"].endswith("..."))
            self.assertTrue(payload["discussion_trace"]["critic_feedback"].endswith("..."))
            self.assertTrue(payload["discussion_trace"]["synthesis_output"].endswith("..."))


if __name__ == "__main__":
    unittest.main()

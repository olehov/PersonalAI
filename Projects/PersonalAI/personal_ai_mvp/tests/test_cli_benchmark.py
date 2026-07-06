from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.cli_test_support import CliTestSupport


class BenchmarkCliTests(CliTestSupport):
    def test_benchmark_pack_outputs_json_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "repo-analysis",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the correct project.",
                        "workflow": "agent",
                        "scope_dirs": ["Projects"],
                        "prompt": "Inspect Minishell.",
                        "expected_signals": ["correct repo"],
                        "anti_signals": ["wrong repo"],
                        "notes": ["smoke test"],
                    }
                ],
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "benchmark-pack",
                    "--pack-file",
                    str(pack_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["pack_id"], "repo-aware-v1")
            self.assertEqual(len(payload["tasks"]), 1)
            self.assertEqual(payload["tasks"][0]["workflow"], "agent")

    def test_benchmark_pack_filters_by_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the correct project.",
                        "workflow": "agent",
                    },
                    {
                        "task_id": "two",
                        "category": "execution_honesty",
                        "title": "Stay honest",
                        "objective": "Avoid fake claims.",
                        "workflow": "agent",
                    },
                ],
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "benchmark-pack",
                    "--pack-file",
                    str(pack_path),
                    "--task-id",
                    "two",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload["tasks"]), 1)
            self.assertEqual(payload["tasks"][0]["task_id"], "two")

    def test_benchmark_run_executes_task_and_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the correct project.",
                        "workflow": "agent",
                        "scope_dirs": ["Projects"],
                        "prompt": "Inspect Minishell.",
                    }
                ],
            )

            with patch(
                "personal_ai.cli.BenchmarkRunService.run_task",
                return_value=type(
                    "BenchmarkResult",
                    (),
                    {
                        "pack_id": "repo-aware-v1",
                        "task_id": "one",
                        "category": "repository_analysis",
                        "workflow": "agent",
                        "model": "deepseek-r1:8b",
                        "status": "needs_execution_layer",
                        "scope_dirs": ("Projects",),
                        "prompt_text": "Inspect Minishell.",
                        "latency_ms": 45,
                        "result_payload": {"status": "needs_execution_layer", "final_output": "Goal"},
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "benchmark-run",
                        "--pack-file",
                        str(pack_path),
                        "--task-id",
                        "one",
                        "--model",
                        "deepseek-r1:8b",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task_id"], "one")
            self.assertEqual(payload["workflow"], "agent")
            self.assertEqual(payload["model"], "deepseek-r1:8b")

    def test_benchmark_history_reads_persisted_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_db = root / ".personal_ai" / "query_history.sqlite3"

            from personal_ai.application.benchmark_run_service import BenchmarkRunResult
            from personal_ai.infrastructure.query_history_repository import SQLiteQueryHistoryRepository

            repository = SQLiteQueryHistoryRepository(history_db)
            repository.save_benchmark_run_result(
                BenchmarkRunResult(
                    pack_id="repo-aware-v1",
                    task_id="execution-honesty-minishell-build",
                    category="execution_honesty",
                    workflow="agent",
                    model="deepseek-r1:8b",
                    status="needs_execution_layer",
                    scope_dirs=("Projects",),
                    prompt_text="Build minishell.",
                    latency_ms=50,
                    result_payload={"status": "needs_execution_layer"},
                )
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--history-db",
                    str(history_db),
                    "--format",
                    "json",
                    "benchmark-history",
                    "--limit",
                    "5",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["pack_id"], "repo-aware-v1")
            self.assertEqual(payload[0]["task_id"], "execution-honesty-minishell-build")

    def test_benchmark_compare_outputs_json_entries_for_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the correct project.",
                        "workflow": "agent",
                        "prompt": "Inspect Minishell.",
                    }
                ],
            )

            with patch(
                "personal_ai.cli.BenchmarkRunService.compare_models",
                return_value=type(
                    "BenchmarkCompare",
                    (),
                    {
                        "pack_id": "repo-aware-v1",
                        "task_ids": ("one",),
                        "entries": (
                            type(
                                "Entry",
                                (),
                                {
                                    "model": "gemma:latest",
                                    "task_id": "one",
                                    "workflow": "agent",
                                    "status": "needs_execution_layer",
                                    "latency_ms": 40,
                                    "result_payload": {"status": "needs_execution_layer"},
                                },
                            )(),
                            type(
                                "Entry",
                                (),
                                {
                                    "model": "deepseek-r1:8b",
                                    "task_id": "one",
                                    "workflow": "agent",
                                    "status": "needs_execution_layer",
                                    "latency_ms": 55,
                                    "result_payload": {"status": "needs_execution_layer"},
                                },
                            )(),
                        ),
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "benchmark-compare",
                        "--pack-file",
                        str(pack_path),
                        "--task-id",
                        "one",
                        "--model",
                        "gemma:latest",
                        "--model",
                        "deepseek-r1:8b",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task_ids"], ["one"])
            self.assertEqual(len(payload["entries"]), 2)
            self.assertEqual(payload["entries"][0]["model"], "gemma:latest")

    def test_benchmark_compare_outputs_whole_pack_when_task_not_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the correct project.",
                        "workflow": "agent",
                    },
                    {
                        "task_id": "two",
                        "category": "execution_honesty",
                        "title": "Stay honest",
                        "objective": "Avoid fake claims.",
                        "workflow": "agent",
                    },
                ],
            )

            with patch(
                "personal_ai.cli.BenchmarkRunService.compare_models",
                return_value=type(
                    "BenchmarkCompare",
                    (),
                    {
                        "pack_id": "repo-aware-v1",
                        "task_ids": ("one", "two"),
                        "entries": (),
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "benchmark-compare",
                        "--pack-file",
                        str(pack_path),
                        "--model",
                        "gemma:latest",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task_ids"], ["one", "two"])

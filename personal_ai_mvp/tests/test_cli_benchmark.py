from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from application.benchmark.pack_service import RepoBenchmarkTask, RepoBenchmarkTurn
from application.benchmark.run_service import BenchmarkRunService
from application.web_search.service import WebSearchResponse, WebSearchResult
from domain.models import (
    AgentRuntimeArtifact,
    GeneratedAnswer,
    PromptMessage,
)
from tests.cli_test_support import CliTestSupport
from tests.path_test_support import history_db_path


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
                        "web_grounding_mode": "required",
                        "web_grounding_query": "latest minishell parser docs",
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
            self.assertEqual(payload["tasks"][0]["web_grounding_mode"], "required")
            self.assertEqual(payload["tasks"][0]["web_grounding_query"], "latest minishell parser docs")

    def test_benchmark_pack_outputs_multi_turn_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "continuation-bsq",
                        "category": "multi_turn_continuation",
                        "title": "Continue BSQ task",
                        "objective": "Check whether the benchmark pack stores follow-up turns.",
                        "workflow": "ask",
                        "prompt": "Build a BSQ first pass.",
                        "turns": [
                            {
                                "prompt": "Generate the initial file layout for BSQ in C.",
                                "expected_signals": ["bsq.c"],
                            },
                            {
                                "prompt": "Now continue and finish the implementation.",
                                "anti_signals": ["restart from scratch"],
                            },
                        ],
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
            self.assertEqual(len(payload["tasks"][0]["turns"]), 2)
            self.assertEqual(
                payload["tasks"][0]["turns"][1]["prompt"],
                "Now continue and finish the implementation.",
            )

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

    def test_benchmark_pack_filters_by_category(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "multi_turn_continuation",
                        "title": "Continue",
                        "objective": "Keep continuity.",
                        "workflow": "ask",
                    },
                    {
                        "task_id": "two",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the right repo.",
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
                    "--category",
                    "multi_turn_continuation",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload["tasks"]), 1)
            self.assertEqual(payload["tasks"][0]["task_id"], "one")

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
                "application.benchmark.run_service.BenchmarkRunService.run_task",
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
            history_db = history_db_path(root)

            from application.benchmark.run_service import BenchmarkRunResult
            from infrastructure.history.repository import SQLiteQueryHistoryRepository

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
                "application.benchmark.run_service.BenchmarkRunService.compare_models",
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
                "application.benchmark.run_service.BenchmarkRunService.compare_models",
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

    def test_benchmark_compare_filters_by_category(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_path = self._write_benchmark_pack(
                root,
                tasks=[
                    {
                        "task_id": "one",
                        "category": "multi_turn_continuation",
                        "title": "Continue",
                        "objective": "Keep continuity.",
                        "workflow": "ask",
                    },
                    {
                        "task_id": "two",
                        "category": "repository_analysis",
                        "title": "Analyze repo",
                        "objective": "Pick the right repo.",
                        "workflow": "agent",
                    },
                ],
            )

            with patch(
                "application.benchmark.run_service.BenchmarkRunService.compare_models",
                return_value=type(
                    "BenchmarkCompare",
                    (),
                    {
                        "pack_id": "repo-aware-v1",
                        "task_ids": ("one",),
                        "entries": (),
                    },
                )(),
            ) as compare_mock:
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "benchmark-compare",
                        "--pack-file",
                        str(pack_path),
                        "--category",
                        "multi_turn_continuation",
                        "--model",
                        "gemma:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task_ids"], ["one"])
            compare_tasks = compare_mock.call_args.kwargs["tasks"]
            self.assertEqual(len(compare_tasks), 1)
            self.assertEqual(compare_tasks[0].task_id, "one")

    def test_multi_turn_benchmark_run_passes_conversation_history_between_turns(self) -> None:
        service = BenchmarkRunService(
            chat_service=_FakeChatService(),
            agent_runtime_service=_FakeAgentRuntimeService(),
        )
        task = RepoBenchmarkTask(
            task_id="continuation-bsq",
            category="multi_turn_continuation",
            title="Continue BSQ task",
            objective="Check whether follow-up prompts see prior turns.",
            workflow="ask",
            scope_dirs=("Projects", "Languages/C"),
            prompt="Generate BSQ incrementally.",
            turns=(
                RepoBenchmarkTurn(prompt="Create the initial BSQ file tree."),
                RepoBenchmarkTurn(prompt="Continue and finish the implementation."),
            ),
        )

        result = service.run_task(
            pack_id="repo-aware-v1",
            task=task,
            model="gpt-oss:20b",
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.result_payload["turn_count"], 2)
        turn_results = result.result_payload["turn_results"]
        self.assertEqual(turn_results[0]["result_payload"]["answer_text"], "draft-1")
        self.assertEqual(turn_results[1]["result_payload"]["answer_text"], "draft-2")
        self.assertEqual(len(service._chat_service.ask_calls), 2)  # type: ignore[attr-defined]
        first_history = service._chat_service.ask_calls[0]["conversation_history"]  # type: ignore[attr-defined]
        second_history = service._chat_service.ask_calls[1]["conversation_history"]  # type: ignore[attr-defined]
        self.assertEqual(first_history, ())
        self.assertEqual(len(second_history), 2)
        self.assertEqual(second_history[0].role, "user")
        self.assertEqual(second_history[0].content, "Create the initial BSQ file tree.")
        self.assertEqual(second_history[1].role, "assistant")
        self.assertEqual(second_history[1].content, "draft-1")

    def test_multi_turn_agent_benchmark_uses_final_output_for_history(self) -> None:
        service = BenchmarkRunService(
            chat_service=_FakeChatService(),
            agent_runtime_service=_FakeAgentRuntimeService(),
        )
        task = RepoBenchmarkTask(
            task_id="continuation-agent",
            category="multi_turn_continuation",
            title="Continue agent task",
            objective="Check whether agent final output is fed into follow-up turns.",
            workflow="agent",
            scope_dirs=("Projects",),
            turns=(
                RepoBenchmarkTurn(prompt="Inspect the repo and propose the first slice."),
                RepoBenchmarkTurn(prompt="Continue from your previous slice and refine it."),
            ),
        )

        result = service.run_task(
            pack_id="repo-aware-v1",
            task=task,
            model="gpt-oss:20b",
        )

        self.assertEqual(result.status, "needs_execution_layer")
        second_history = service._agent_runtime_service.calls[1]["conversation_history"]  # type: ignore[attr-defined]
        self.assertEqual(len(second_history), 2)
        self.assertEqual(second_history[1].content, "agent-draft-1")

    def test_benchmark_run_uses_forced_web_grounding_for_ask_workflow(self) -> None:
        web_search_service = _FakeWebSearchService()
        chat_service = _FakeChatService()
        service = BenchmarkRunService(
            chat_service=chat_service,
            agent_runtime_service=_FakeAgentRuntimeService(),
            web_search_service=web_search_service,
        )
        task = RepoBenchmarkTask(
            task_id="web-grounded-bsq",
            category="web_grounded_answer",
            title="Web-grounded BSQ answer",
            objective="Force a web-grounded run for comparison.",
            workflow="ask",
            scope_dirs=("Projects", "Languages/C"),
            prompt="Give the latest BSQ advice.",
            web_grounding_mode="required",
            web_grounding_query="latest bsq c implementation best practices",
        )

        result = service.run_task(
            pack_id="repo-aware-v1",
            task=task,
            model="gpt-oss:20b",
        )

        self.assertEqual(web_search_service.queries, ["latest bsq c implementation best practices"])
        self.assertIsNotNone(chat_service.ask_calls[0]["web_search_response"])
        self.assertEqual(
            chat_service.ask_calls[0]["web_search_response"].query,
            "latest bsq c implementation best practices",
        )
        metadata = result.result_payload["benchmark_metadata"]
        self.assertEqual(metadata["web_grounding_mode"], "required")
        self.assertTrue(metadata["web_grounding_used"])
        self.assertEqual(metadata["web_grounding_effective_query"], "latest bsq c implementation best practices")

    def test_benchmark_run_skips_web_grounding_when_disabled(self) -> None:
        web_search_service = _FakeWebSearchService()
        chat_service = _FakeChatService()
        service = BenchmarkRunService(
            chat_service=chat_service,
            agent_runtime_service=_FakeAgentRuntimeService(),
            web_search_service=web_search_service,
        )
        task = RepoBenchmarkTask(
            task_id="vault-only-bsq",
            category="vault_only_answer",
            title="Vault-only BSQ answer",
            objective="Keep the same prompt without web grounding.",
            workflow="ask",
            scope_dirs=("Projects", "Languages/C"),
            prompt="Give the latest BSQ advice.",
            web_grounding_mode="disabled",
        )

        result = service.run_task(
            pack_id="repo-aware-v1",
            task=task,
            model="gpt-oss:20b",
        )

        self.assertEqual(web_search_service.queries, [])
        self.assertIsNone(chat_service.ask_calls[0]["web_search_response"])
        metadata = result.result_payload["benchmark_metadata"]
        self.assertEqual(metadata["web_grounding_mode"], "disabled")
        self.assertFalse(metadata["web_grounding_used"])


class _FakeChatService:
    def __init__(self) -> None:
        self.ask_calls: list[dict[str, object]] = []

    def ask(
        self,
        question: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        web_search_response: WebSearchResponse | None = None,
    ) -> GeneratedAnswer:
        self.ask_calls.append(
            {
                "question": question,
                "model": model,
                "scope_dirs": scope_dirs,
                "conversation_history": conversation_history,
                "reasoning_mode": reasoning_mode,
                "web_search_response": web_search_response,
            }
        )
        return GeneratedAnswer(
            model=model,
            question=question,
            answer_text=f"draft-{len(self.ask_calls)}",
        )

    def scope_implementation(
        self,
        question: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        web_search_response: WebSearchResponse | None = None,
    ) -> GeneratedAnswer:
        return self.ask(
            question,
            model=model,
            scope_dirs=scope_dirs,
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
            web_search_response=web_search_response,
        )


class _FakeAgentRuntimeService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(
        self,
        request_text: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        discussion_preset: str | None = None,
    ) -> AgentRuntimeArtifact:
        self.calls.append(
            {
                "request_text": request_text,
                "model": model,
                "scope_dirs": scope_dirs,
                "conversation_history": conversation_history,
                "reasoning_mode": reasoning_mode,
                "discussion_preset": discussion_preset,
            }
        )
        index = len(self.calls)
        return AgentRuntimeArtifact(
            model=model,
            request_text=request_text,
            normalized_goal=request_text,
            task_mode="implementation",
            status="needs_execution_layer",
            scope_dirs=scope_dirs,
            final_output=f"agent-draft-{index}",
        )


class _FakeWebSearchService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def search(self, query: str) -> WebSearchResponse:
        self.queries.append(query)
        return WebSearchResponse(
            query=query,
            provider="fake-search",
            results=(
                WebSearchResult(
                    title="BSQ reference",
                    url="https://example.com/bsq",
                    snippet="Fresh BSQ guidance.",
                    source="example.com",
                ),
            ),
            enabled=True,
            original_query=query,
            requested_max_results=1,
            applied_max_results=1,
            raw_result_count=1,
        )

from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from domain.model_parts.knowledge import GeneratedAnswer
from domain.models import PromptMessage
from web_app.http import handle_api_request
from tests.web_ui_test_support import build_app, seed_agent_history


class _MetaLeakThenRepairClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[PromptMessage, ...], dict[str, object] | None]] = []
        self._repair_calls = 0

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
        if "Recursive Refinement Critique:" in last_message:
            return "Strengths\n- Structured.\n\nIssues\n- Incomplete.\n\nMissing Grounding\n- Need completion.\n\nImprove\n- Finish it."
        if "Recursive Refinement Final Pass:" in last_message:
            return "Architecture\n- Draft only.\n\nCode Skeleton\n```c\nint solve_bsq("
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

    def list_models(self) -> list[str]:
        return ["gpt-oss:20b"]


class _FakePromptPreprocessor:
    def __init__(self, processed_text: str) -> None:
        self.processed_text = processed_text
        self.calls: list[tuple[str, str | None]] = []
        self.translator_output = processed_text
        self.translator_error = None
        self.fallback_reason = None

    def preprocess(self, text: str, *, workflow_hint: str | None = None):  # type: ignore[no-untyped-def]
        self.calls.append((text, workflow_hint))

        class _Result:
            def __init__(
                self,
                original_text: str,
                processed_text: str,
                translator_output: str | None,
                translator_error: str | None,
                fallback_reason: str | None,
            ) -> None:
                self.original_text = original_text
                self.processed_text = processed_text
                self.mode = "test-double"
                self.applied = original_text != processed_text
                self.translator_output = translator_output
                self.translator_error = translator_error
                self.fallback_reason = fallback_reason

        return _Result(
            text,
            self.processed_text,
            self.translator_output,
            self.translator_error,
            self.fallback_reason,
        )


class _FakeWebSearchService:
    def __init__(self, response) -> None:
        self.enabled = True
        self._response = response
        self.queries: list[str] = []

    def search(self, query: str):  # type: ignore[no-untyped-def]
        self.queries.append(query)
        return self._response


class WebUIApiTests(unittest.TestCase):
    def test_handle_api_request_supports_health_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nRuntime overview.\n",
                encoding="utf-8",
            )
            app = build_app(root)

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/health",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["vault_loaded"])
            self.assertEqual(payload["note_count"], 1)

    def test_handle_api_request_validates_ask_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir(parents=True)
            (root / "Projects" / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            app = build_app(root)

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/ask",
                body=json.dumps({"question": ""}),
            )

            self.assertEqual(status_code, 400)
            self.assertEqual(payload["error"], "Question is required.")

    def test_handle_api_request_supports_implementation_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            app.scope_implementation = lambda **kwargs: {  # type: ignore[method-assign]
                "model": kwargs["model"],
                "question": kwargs["request_text"],
                "answer_text": "Goal\nConstraints\nModules\nIncremental Slices\nFirst Slice\nValidation",
                "citations": ["Projects/Shell.md"],
                "prompt": {
                    "task_mode": "implementation",
                    "retrieval": {"primary_notes": [], "related_notes": []},
                },
            }

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/implementation-scope",
                body=json.dumps(
                    {
                        "request_text": "Build the mandatory part of minishell.",
                        "model": "deepseek-r1:8b",
                        "scope_text": "Projects",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["model"], "deepseek-r1:8b")
            self.assertIn("Incremental Slices", payload["result"]["answer_text"])
            self.assertEqual(payload["result"]["execution"]["requested_workflow"], "implementation")
            self.assertEqual(payload["result"]["execution"]["executed_workflow"], "implementation")
            self.assertEqual(payload["result"]["execution"]["resolved_model"], "deepseek-r1:8b")

    def test_handle_api_request_supports_agent_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}
            def fake_run_agent(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                "model": kwargs["model"],
                "executor_model": "qwen2.5-coder:7b",
                "critic_model": "gemma:latest",
                "synthesis_model": "deepseek-r1:8b",
                "discussion_preset": kwargs.get("discussion_preset"),
                "history_entry_id": 7,
                "request_text": kwargs["request_text"],
                "normalized_goal": "build minishell",
                "task_mode": "implementation",
                "status": "needs_execution_layer",
                "scope_dirs": ["Projects"],
                "citations": ["Projects/Minishell.md"],
                "steps": [
                    {
                        "step_index": 1,
                        "kind": "retrieval",
                        "title": "Grounded Retrieval",
                        "input_text": "build minishell",
                        "output_text": "question=build minishell",
                        "observation": "Retrieved 1 primary note.",
                    }
                ],
                "recommended_actions": [
                    {
                        "action_type": "inspect_note",
                        "title": "Inspect Primary Knowledge Note",
                        "target": "Projects/Minishell.md",
                        "instruction": "Read the highest-priority grounded note.",
                        "rationale": "Ground execution in vault context.",
                    }
                ],
                "action_executions": [
                    {
                        "action_type": "inspect_note",
                        "target": "Projects/Minishell.md",
                        "status": "executed",
                        "output_text": "title=Minishell",
                    }
                ],
                "overview": {
                    "step_count": 1,
                    "recommended_action_count": 1,
                    "executed_action_count": 1,
                    "deferred_action_count": 0,
                    "failed_action_count": 0,
                    "citation_count": 1,
                    "planned_task_count": 2,
                },
                "task_plan": {
                    "goal": "build minishell",
                    "current_focus": "Add the parser entrypoint stub.",
                    "summary": "2 planned implementation tasks. Retrieval and planning are complete; execution is still pending.",
                    "entries": [
                        {
                            "step_index": 1,
                            "title": "Add the parser entrypoint stub.",
                            "status": "next",
                            "details": "Add the parser entrypoint stub.",
                            "source_section": "Incremental Slices",
                        }
                    ],
                    "validation_checks": ["make all"],
                },
                "final_output": "Goal\nConstraints\nModules\nFirst Slice\nValidation",
                "discussion_trace": {
                    "preset": kwargs.get("discussion_preset") or "custom",
                    "planner_draft": "Planner draft",
                    "critic_feedback": "Critic feedback",
                    "synthesis_output": "Synthesis output",
                    "fallback_used": None,
                },
                "prompt": None,
            }
            app.run_agent = fake_run_agent  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/agent-runtime",
                body=json.dumps(
                    {
                        "request_text": "Build the mandatory part of minishell.",
                        "model": "deepseek-r1:8b",
                        "scope_text": "Projects",
                        "discussion_preset": "coder_critic",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["model"], "deepseek-r1:8b")
            self.assertEqual(payload["result"]["status"], "needs_execution_layer")
            self.assertEqual(payload["result"]["executor_model"], "qwen2.5-coder:7b")
            self.assertEqual(payload["result"]["steps"][0]["kind"], "retrieval")
            self.assertEqual(
                payload["result"]["recommended_actions"][0]["action_type"],
                "inspect_note",
            )
            self.assertEqual(
                payload["result"]["action_executions"][0]["status"],
                "executed",
            )
            self.assertEqual(
                payload["result"]["task_plan"]["entries"][0]["status"],
                "next",
            )
            self.assertEqual(payload["result"]["history_entry_id"], 7)
            self.assertEqual(payload["result"]["discussion_preset"], "coder_critic")
            self.assertEqual(payload["result"]["critic_model"], "gemma:latest")
            self.assertEqual(payload["result"]["synthesis_model"], "deepseek-r1:8b")
            self.assertEqual(payload["result"]["discussion_trace"]["critic_feedback"], "Critic feedback")
            self.assertEqual(captured["discussion_preset"], "coder_critic")

    def test_handle_api_request_leaves_agent_model_blank_for_agent_default_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}

            def fake_run_agent(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": "qwen2.5-coder:7b",
                    "request_text": kwargs["request_text"],
                    "normalized_goal": "build minishell",
                    "task_mode": "implementation",
                    "status": "needs_execution_layer",
                    "scope_dirs": ["Projects"],
                    "citations": [],
                    "steps": [],
                    "recommended_actions": [],
                    "action_executions": [],
                    "overview": {
                        "step_count": 0,
                        "recommended_action_count": 0,
                        "executed_action_count": 0,
                        "deferred_action_count": 0,
                        "failed_action_count": 0,
                        "citation_count": 0,
                        "planned_task_count": 0,
                    },
                    "final_output": "Goal\nConstraints",
                    "prompt": None,
                }

            app.run_agent = fake_run_agent  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/agent-runtime",
                body=json.dumps(
                    {
                        "request_text": "Build the mandatory part of minishell.",
                        "scope_text": "Projects",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["model"], "qwen2.5-coder:7b")
            self.assertEqual(captured["model"], "")

    def test_handle_api_request_supports_agent_task_plan_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            entry_id = seed_agent_history(app)

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/agent-task-plan",
                body=json.dumps(
                    {
                        "entry_id": entry_id,
                        "task_plan": {
                            "goal": "build minishell",
                            "current_focus": "Parser stub",
                            "summary": "1 planned implementation task.",
                            "entries": [
                                {
                                    "step_index": 1,
                                    "title": "Parser stub",
                                    "status": "next",
                                    "details": "Add parser entrypoint.",
                                    "source_section": "Incremental Slices",
                                }
                            ],
                            "validation_checks": ["make all"],
                        },
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["task_plan"]["goal"], "build minishell")
            self.assertEqual(payload["result"]["task_plan"]["entries"][0]["status"], "next")

    def test_handle_api_request_supports_analyze_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Languages" / "C" / "File IO in C.md").write_text(
                "# File I/O in C\n[[Error Handling in C]]\n[[stdio]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Error Handling in C.md").write_text(
                "# Error Handling in C\n[[File IO in C]]\n",
                encoding="utf-8",
            )

            app = build_app(root)
            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/analyze-dir",
                body=json.dumps({"directory": "Languages/C"}),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["directory"], "Languages/C")
            self.assertEqual(payload["result"]["note_count"], 2)
            self.assertEqual(payload["result"]["execution"]["requested_workflow"], "analyze")
            self.assertEqual(payload["result"]["execution"]["executed_workflow"], "analyze")
            self.assertIsNone(payload["result"]["execution"]["resolved_model"])

    def test_handle_api_request_supports_auto_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-route",
                body=json.dumps({"prompt": "Write a note about C parser cleanup rules."}),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "draft")

    def test_handle_api_request_auto_route_uses_prompt_preprocessor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            fake_preprocessor = _FakePromptPreprocessor("Write a note about parser cleanup.")
            app._prompt_preprocessor = fake_preprocessor  # type: ignore[attr-defined]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-route",
                body=json.dumps({"prompt": "opaque prompt"}),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "draft")
            self.assertEqual(fake_preprocessor.calls, [("opaque prompt", "route")])
            self.assertEqual(
                payload["preprocess"]["translator_output"],
                "Write a note about parser cleanup.",
            )

    def test_handle_api_request_supports_auto_route_with_follow_up_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-route",
                body=json.dumps(
                    {
                        "prompt": "you did not finish the task",
                        "chat_history": [
                            {"role": "user", "content": "Generate code for bsq in C."},
                            {"role": "assistant", "content": "Started with a file layout."},
                        ],
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")

    def test_handle_api_request_supports_auto_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}
            def fake_scope_implementation(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                "model": kwargs["model"],
                "question": kwargs["request_text"],
                "answer_text": "Goal\nConstraints\nModules\nIncremental Slices\nFirst Slice\nValidation",
                "citations": ["Projects/Shell.md"],
                "prompt": {
                    "task_mode": "implementation",
                    "retrieval": {"primary_notes": [], "related_notes": []},
                },
            }
            app.scope_implementation = fake_scope_implementation  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "Break the task into implementation slices for minishell.",
                        "model": "deepseek-r1:8b",
                        "scope_text": "Projects",
                        "discussion_preset": "heavy_synthesis",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")
            self.assertEqual(payload["route"]["reasoning_mode"], "high")
            self.assertEqual(payload["reasoning_mode"], "high")
            self.assertEqual(payload["result"]["model"], "deepseek-r1:8b")
            self.assertEqual(payload["execution"]["requested_workflow"], "auto")
            self.assertEqual(payload["execution"]["executed_workflow"], "implementation")
            self.assertEqual(payload["execution"]["route_workflow"], "implementation")
            self.assertNotIn("discussion_preset", captured)

    def test_handle_api_request_auto_run_includes_web_grounding_policy_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            app._web_search = _FakeWebSearchService(  # type: ignore[attr-defined]
                SimpleNamespace(
                    query="latest python asyncio docs",
                    original_query="latest python asyncio docs with release notes",
                    query_truncated=True,
                    provider="searxng",
                    enabled=True,
                    requested_max_results=8,
                    applied_max_results=5,
                    raw_result_count=5,
                    filtered_result_count=2,
                    invalid_result_count=1,
                    blocked_result_count=1,
                    allowlist_filtered_count=0,
                    results=(
                        SimpleNamespace(
                            title="asyncio docs",
                            url="https://docs.python.org/3/library/asyncio.html",
                            snippet="Coroutines and tasks.",
                            source="python docs",
                        ),
                    ),
                )
            )

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "Look up the latest Python asyncio docs and summarize changes.",
                        "model": "gpt-oss:20b",
                        "scope_text": "Projects, Languages/C",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "ask")
            self.assertEqual(payload["result"]["web_grounding"]["provider"], "searxng")
            self.assertTrue(payload["result"]["web_grounding"]["query_truncated"])
            self.assertEqual(
                payload["result"]["web_grounding"]["policy"]["requested_max_results"],
                8,
            )
            self.assertEqual(
                payload["result"]["web_grounding"]["policy"]["blocked_result_count"],
                1,
            )
            self.assertEqual(
                payload["result"]["web_grounding"]["results"][0]["url"],
                "https://docs.python.org/3/library/asyncio.html",
            )

    def test_handle_api_request_auto_run_uses_prompt_preprocessor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            fake_preprocessor = _FakePromptPreprocessor(
                "Break the task into implementation slices for minishell."
            )
            app._prompt_preprocessor = fake_preprocessor  # type: ignore[attr-defined]
            captured: dict[str, object] = {}

            def fake_scope_implementation(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": kwargs["model"],
                    "question": kwargs["request_text"],
                    "answer_text": "Goal\nConstraints\nModules\nIncremental Slices\nFirst Slice\nValidation",
                    "citations": [],
                    "prompt": {
                        "task_mode": "implementation",
                        "retrieval": {"primary_notes": [], "related_notes": []},
                    },
                }

            app.scope_implementation = fake_scope_implementation  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "opaque prompt",
                        "model": "deepseek-r1:8b",
                        "scope_text": "Projects",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")
            self.assertEqual(
                captured["request_text"],
                "Break the task into implementation slices for minishell.",
            )
            self.assertEqual(fake_preprocessor.calls, [("opaque prompt", "auto")])
            self.assertEqual(
                payload["preprocess"]["translator_output"],
                "Break the task into implementation slices for minishell.",
            )

    def test_handle_api_request_auto_run_preprocesses_only_once_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            fake_preprocessor = _FakePromptPreprocessor(
                "Break the task into implementation slices for minishell."
            )
            app._prompt_preprocessor = fake_preprocessor  # type: ignore[attr-defined]

            def fake_scope_implementation(question, **kwargs):  # type: ignore[no-untyped-def]
                return GeneratedAnswer(
                    model=kwargs["model"],
                    question=question,
                    answer_text="Goal\nConstraints\nModules\nIncremental Slices\nFirst Slice\nValidation",
                    citations=(),
                    prompt=None,
                )

            app._chat.scope_implementation = fake_scope_implementation  # type: ignore[attr-defined]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "opaque prompt",
                        "model": "deepseek-r1:8b",
                        "scope_text": "Projects",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")
            self.assertEqual(fake_preprocessor.calls, [("opaque prompt", "auto")])

    def test_handle_api_request_passes_chat_history_to_ask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}

            def fake_ask(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": kwargs["model"],
                    "question": kwargs["question"],
                    "answer_text": "Follow-up answer",
                    "citations": [],
                    "prompt": {
                        "task_mode": "general",
                        "retrieval": {"primary_notes": [], "related_notes": []},
                    },
                }

            app.ask = fake_ask  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/ask",
                body=json.dumps(
                    {
                        "question": "Continue the parser discussion.",
                        "model": "gemma:latest",
                        "scope_text": "Projects",
                        "chat_history": [
                            {"role": "user", "content": "We started with tokenization."},
                            {"role": "assistant", "content": "Next step should stay narrow."},
                        ],
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["answer_text"], "Follow-up answer")
            self.assertEqual(len(captured["conversation_history"]), 2)
            self.assertEqual(captured["conversation_history"][0].role, "user")

    def test_handle_api_request_supports_ask_execution_debug_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/ask",
                body=json.dumps(
                    {
                        "question": "Compare parser designs.",
                        "model": "gemma:latest",
                        "reasoning_mode": "high",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["execution"]["requested_workflow"], "ask")
            self.assertEqual(payload["result"]["execution"]["executed_workflow"], "ask")
            self.assertEqual(payload["result"]["execution"]["resolved_model"], "gemma:latest")
            self.assertEqual(payload["result"]["execution"]["reasoning_mode"], "high")

    def test_handle_api_request_passes_chat_history_through_auto_run_to_ask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}

            def fake_ask(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": kwargs["model"],
                    "question": kwargs["question"],
                    "answer_text": "Context-aware follow-up answer",
                    "citations": [],
                    "prompt": {
                        "task_mode": "general",
                        "retrieval": {"primary_notes": [], "related_notes": []},
                    },
                }

            app.ask = fake_ask  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "Summarize the parser discussion so far.",
                        "model": "gpt-oss:20b",
                        "scope_text": "Projects, Languages/C",
                        "chat_history": [
                            {"role": "user", "content": "Generate code for bsq in C."},
                            {"role": "assistant", "content": "Started with file layout and header skeleton."},
                        ],
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "ask")
            self.assertEqual(payload["result"]["answer_text"], "Context-aware follow-up answer")
            self.assertEqual(len(captured["conversation_history"]), 2)
            self.assertEqual(captured["conversation_history"][0].content, "Generate code for bsq in C.")
            self.assertEqual(captured["conversation_history"][1].role, "assistant")

    def test_handle_api_request_locks_follow_up_auto_run_to_previous_implementation_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}

            def fake_scope_implementation(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": kwargs["model"],
                    "question": kwargs["request_text"],
                    "answer_text": "Completed implementation follow-up",
                    "citations": [],
                    "prompt": {
                        "task_mode": "implementation",
                        "retrieval": {"primary_notes": [], "related_notes": []},
                    },
                }

            app.scope_implementation = fake_scope_implementation  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "you did not finish the task",
                        "model": "gpt-oss:20b",
                        "scope_text": "Projects, Languages/C",
                        "chat_history": [
                            {"role": "user", "content": "Generate code for bsq in C."},
                            {"role": "assistant", "content": "Started with a file layout and partial code."},
                        ],
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")
            self.assertEqual(payload["result"]["answer_text"], "Completed implementation follow-up")
            self.assertEqual(captured["request_text"], "you did not finish the task")

    def test_handle_api_request_auto_run_repairs_follow_up_meta_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BSQ.md").write_text(
                "# BSQ\nDynamic programming, memory cleanup, and output rendering in C.\n",
                encoding="utf-8",
            )
            app = build_app(root)
            fake_client = _MetaLeakThenRepairClient()
            app._chat._ollama_client = fake_client  # type: ignore[attr-defined]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/auto-run",
                body=json.dumps(
                    {
                        "prompt": "you did not finish the task",
                        "model": "gpt-oss:20b",
                        "scope_text": "Projects, Languages/C",
                        "reasoning_mode": "high",
                        "chat_history": [
                            {
                                "role": "user",
                                "content": "Generate code for bsq in C with architecture, modules, execution flow, edge cases, and code skeleton.",
                            },
                            {
                                "role": "assistant",
                                "content": (
                                    "Architecture\n- Use dynamic programming.\n\n"
                                    "Code Skeleton\n```c\nint **mat = malloc(rows * sizeof(int *));\n"
                                ),
                            },
                        ],
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["route"]["workflow"], "implementation")
            self.assertIn("Execution Flow", payload["result"]["answer_text"])
            self.assertIn("int solve_bsq(void)", payload["result"]["answer_text"])
            self.assertEqual(len(fake_client.calls), 5)
            self.assertIn("Implementation Answer Repair Pass:", fake_client.calls[3][1][-1].content)
            self.assertIn(
                "The answer leaked internal repair or planning commentary",
                fake_client.calls[4][1][-1].content,
            )

    def test_handle_api_request_passes_reasoning_mode_to_ask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            captured: dict[str, object] = {}

            def fake_ask(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs)
                return {
                    "model": kwargs["model"],
                    "question": kwargs["question"],
                    "answer_text": "Focused answer",
                    "citations": [],
                    "prompt": {
                        "task_mode": "general",
                        "retrieval": {"primary_notes": [], "related_notes": []},
                    },
                }

            app.ask = fake_ask  # type: ignore[method-assign]

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/ask",
                body=json.dumps(
                    {
                        "question": "Compare parser designs.",
                        "model": "gemma:latest",
                        "reasoning_mode": "high",
                    }
                ),
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["result"]["answer_text"], "Focused answer")
            self.assertEqual(captured["reasoning_mode"], "high")

    def test_handle_api_request_returns_stable_error_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)

            status_code, payload = handle_api_request(
                app,
                method="POST",
                path="/api/ask",
                body="{not-json",
            )

            self.assertEqual(status_code, 400)
            self.assertEqual(payload["error"], "Invalid JSON body.")

    def test_handle_api_request_hides_internal_errors_by_default(self) -> None:
        previous = os.environ.get("PERSONAL_AI_DEBUG_API_ERRORS")
        try:
            os.environ.pop("PERSONAL_AI_DEBUG_API_ERRORS", None)
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                app = build_app(root)

                def fake_ask(**kwargs):  # type: ignore[no-untyped-def]
                    raise RuntimeError("sensitive path H:/Projects/PersonalAI/secret.txt")

                app.ask = fake_ask  # type: ignore[method-assign]

                status_code, payload = handle_api_request(
                    app,
                    method="POST",
                    path="/api/ask",
                    body=json.dumps({"question": "Break parser work down."}),
                )

                self.assertEqual(status_code, 500)
                self.assertEqual(payload["error"], "Internal server error.")
        finally:
            if previous is None:
                os.environ.pop("PERSONAL_AI_DEBUG_API_ERRORS", None)
            else:
                os.environ["PERSONAL_AI_DEBUG_API_ERRORS"] = previous

    def test_handle_api_request_can_expose_internal_errors_in_debug_mode(self) -> None:
        previous = os.environ.get("PERSONAL_AI_DEBUG_API_ERRORS")
        try:
            os.environ["PERSONAL_AI_DEBUG_API_ERRORS"] = "true"
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                app = build_app(root)

                def fake_ask(**kwargs):  # type: ignore[no-untyped-def]
                    raise RuntimeError("sensitive path H:/Projects/PersonalAI/secret.txt")

                app.ask = fake_ask  # type: ignore[method-assign]

                status_code, payload = handle_api_request(
                    app,
                    method="POST",
                    path="/api/ask",
                    body=json.dumps({"question": "Break parser work down."}),
                )

                self.assertEqual(status_code, 500)
                self.assertEqual(payload["error"], "sensitive path H:/Projects/PersonalAI/secret.txt")
        finally:
            if previous is None:
                os.environ.pop("PERSONAL_AI_DEBUG_API_ERRORS", None)
            else:
                os.environ["PERSONAL_AI_DEBUG_API_ERRORS"] = previous

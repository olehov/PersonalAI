from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from personal_ai.web_ui import handle_api_request
from tests.web_ui_test_support import build_app, seed_agent_history


class WebUIApiTests(unittest.TestCase):
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
            self.assertNotIn("discussion_preset", captured)

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

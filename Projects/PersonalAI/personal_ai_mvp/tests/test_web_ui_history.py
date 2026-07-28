from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from web_app.app import DEFAULT_UI_MODEL;
from web_app.http import handle_api_request
from tests.web_ui_test_support import (
    build_app,
    seed_agent_history,
    seed_ask_history,
    seed_benchmark_history,
)


class WebUIHistoryTests(unittest.TestCase):
    def test_personal_ai_web_app_can_analyze_directory(self) -> None:
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
            payload = app.analyze_directory(directory="Languages/C")

            self.assertEqual(payload["directory"], "Languages/C")
            self.assertEqual(payload["note_count"], 2)
            self.assertIn("stdio", payload["unresolved_links"])

    def test_personal_ai_web_app_can_list_ask_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir(parents=True)
            (root / "Projects" / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            app = build_app(root)
            seed_ask_history(app, root)

            payload = app.list_ask_history(limit=5)

            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["model"], DEFAULT_UI_MODEL)
            self.assertEqual(payload[0]["task_mode"], "implementation")

    def test_personal_ai_web_app_detects_built_frontend_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dist_dir = root / "frontend-dist"
            dist_dir.mkdir(parents=True)
            (dist_dir / "index.html").write_text(
                "<!doctype html><div id='root'></div>",
                encoding="utf-8",
            )

            app = build_app(root)
            app._frontend_dist_dir = dist_dir

            self.assertTrue(app.has_frontend_assets())
            self.assertEqual(app.frontend_index_path(), dist_dir / "index.html")

    def test_resolve_frontend_asset_stays_inside_dist_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dist_dir = root / "frontend-dist"
            assets_dir = dist_dir / "assets"
            assets_dir.mkdir(parents=True)
            (dist_dir / "index.html").write_text(
                "<!doctype html><div id='root'></div>",
                encoding="utf-8",
            )
            (assets_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")

            app = build_app(root)
            app._frontend_dist_dir = dist_dir

            self.assertEqual(
                app.resolve_frontend_asset("/assets/app.js"),
                (assets_dir / "app.js").resolve(),
            )
            self.assertEqual(
                app.resolve_frontend_asset("/../../secret.txt"),
                (dist_dir / "index.html").resolve(),
            )

    def test_handle_api_request_returns_history_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir(parents=True)
            (root / "Projects" / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            app = build_app(root)
            seed_ask_history(app, root)

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/ask-history?limit=5",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["history_kind"], "ask")
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["task_mode"], "implementation")

    def test_handle_api_request_returns_agent_history_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            seed_agent_history(app)

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/agent-history?limit=5",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["history_kind"], "agent")
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["model"], "deepseek-r1:8b")
            self.assertEqual(payload["entries"][0]["status"], "needs_execution_layer")

    def test_handle_api_request_returns_benchmark_history_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            seed_benchmark_history(app)

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/benchmark-history?limit=5",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["history_kind"], "benchmark")
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["task_id"], "multi-turn-bsq-c-continuation")
            self.assertEqual(len(payload["entries"][0]["result_payload"]["turn_results"]), 2)

    def test_handle_api_request_returns_history_overview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir(parents=True)
            (root / "Projects" / "Shell.md").write_text(
                "# Shell\nImplement parser and executor modules.\n",
                encoding="utf-8",
            )

            app = build_app(root)
            seed_ask_history(app, root)
            seed_agent_history(app)
            seed_benchmark_history(app)

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/history-overview",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["streams"]["ask"], 1)
            self.assertEqual(payload["streams"]["agent"], 1)
            self.assertEqual(payload["streams"]["benchmark"], 1)

    def test_handle_api_request_returns_available_models(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = build_app(root)
            app._ollama_client = type(
                "FakeOllamaClient",
                (),
                {"list_models": staticmethod(lambda: ["gemma:latest", "qwen2.5:7b"])},
            )()

            status_code, payload = handle_api_request(
                app,
                method="GET",
                path="/api/models",
                body=None,
            )

            self.assertEqual(status_code, 200)
            self.assertEqual(payload["default_model"], DEFAULT_UI_MODEL)
            self.assertEqual(payload["models"], ["gemma:latest", "qwen2.5:7b"])

    def test_personal_ai_web_app_uses_agent_default_model_when_agent_request_model_is_blank(self) -> None:
        previous_agent_default = os.environ.get("PERSONAL_AI_AGENT_DEFAULT_MODEL")
        try:
            os.environ["PERSONAL_AI_AGENT_DEFAULT_MODEL"] = "qwen2.5-coder:7b"
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                app = build_app(root)
                captured: dict[str, object] = {}

                def fake_run(request_text, *, model, **kwargs):  # type: ignore[no-untyped-def]
                    captured["model"] = model
                    return seed_agent_artifact(model)

                app._agent_runtime.run = fake_run  # type: ignore[method-assign]

                payload = app.run_agent(
                    request_text="Build the mandatory part of minishell.",
                    model="",
                    scope_text="Projects",
                )

                self.assertEqual(captured["model"], "qwen2.5-coder:7b")
                self.assertEqual(payload["model"], "qwen2.5-coder:7b")
        finally:
            if previous_agent_default is None:
                os.environ.pop("PERSONAL_AI_AGENT_DEFAULT_MODEL", None)
            else:
                os.environ["PERSONAL_AI_AGENT_DEFAULT_MODEL"] = previous_agent_default


def seed_agent_artifact(model: str) -> object:
    from domain.models import AgentRuntimeArtifact

    return AgentRuntimeArtifact(
        model=model,
        request_text="build minishell",
        normalized_goal="build minishell",
        task_mode="implementation",
        status="needs_execution_layer",
        scope_dirs=("Projects",),
        citations=("Projects/Minishell.md",),
        steps=(),
        final_output="Goal\nConstraints",
    )

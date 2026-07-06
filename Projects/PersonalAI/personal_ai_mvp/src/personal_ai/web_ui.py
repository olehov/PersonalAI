"""Minimal local web UI for testing grounded answers and note drafts."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from personal_ai.application import (
    AgentRuntimeService,
    AnswerService,
    ChatService,
    DirectoryAnalysisService,
    KnowledgeService,
    NoteDraftService,
    NoteMutationService,
    NotePolicy,
    RequestRoutingService,
    RetrievalService,
    serialize_agent_run_history_entry,
    serialize_directory_analysis_report,
    serialize_generated_answer,
    serialize_agent_runtime_artifact,
    serialize_generated_note_draft,
    serialize_query_history_entry,
)
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.query_history_repository import SQLiteQueryHistoryRepository
from personal_ai.infrastructure.env_loader import load_env_file
from personal_ai.web_ui_api import (
    handle_api_request as _handle_api_request,
    normalize_reasoning_mode,
    parse_conversation_history,
    parse_scope_dirs,
    serialize_route_decision,
)

load_env_file()

DEFAULT_UI_MODEL = os.getenv("PERSONAL_AI_DEFAULT_MODEL", "gemma:latest")
DEFAULT_HISTORY_DB_NAME = "query_history.sqlite3"
DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
DEFAULT_FRONTEND_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class PersonalAIWebApp:
    """Thin controller layer for the local web UI."""

    def __init__(
        self,
        *,
        vault_root: Path,
        ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
        ollama_timeout_seconds: int | None = None,
        frontend_dist_dir: Path = DEFAULT_FRONTEND_DIST_DIR,
    ) -> None:
        self._knowledge = KnowledgeService(vault_root)
        self._knowledge.load()
        self._frontend_dist_dir = frontend_dist_dir
        retrieval = RetrievalService(self._knowledge)
        self._directory_analysis = DirectoryAnalysisService(self._knowledge)
        self._router = RequestRoutingService()
        answer_service = AnswerService(retrieval)
        self._ollama_client = OllamaClient(
            base_url=ollama_base_url,
            timeout_seconds=ollama_timeout_seconds,
        )
        self._history_repository = SQLiteQueryHistoryRepository(
            vault_root / ".personal_ai" / DEFAULT_HISTORY_DB_NAME
        )
        mutation_service = NoteMutationService(self._knowledge, NotePolicy(vault_root))
        self._chat = ChatService(answer_service, self._ollama_client, self._history_repository)
        self._agent_runtime = AgentRuntimeService(
            self._knowledge,
            answer_service,
            self._ollama_client,
            self._history_repository,
        )
        self._drafts = NoteDraftService(answer_service, mutation_service, self._ollama_client)

    def reload(self) -> None:
        """Reload the vault index."""
        self._knowledge.load()

    def ask(
        self,
        *,
        question: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
    ) -> dict[str, object]:
        """Run a grounded answer request."""
        answer = self._chat.ask(
            question.strip(),
            model=model.strip(),
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )
        return serialize_generated_answer(answer)

    def scope_implementation(
        self,
        *,
        request_text: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
    ) -> dict[str, object]:
        """Generate a scoped implementation breakdown for a project-scale request."""
        answer = self._chat.scope_implementation(
            request_text.strip(),
            model=model.strip(),
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )
        return serialize_generated_answer(answer)

    def run_agent(
        self,
        *,
        request_text: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        discussion_preset: str | None = None,
    ) -> dict[str, object]:
        """Run the planning-oriented agent runtime."""
        artifact = self._agent_runtime.run(
            request_text.strip(),
            model=model.strip(),
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
            discussion_preset=discussion_preset,
        )
        return serialize_agent_runtime_artifact(artifact)

    def draft_note(
        self,
        *,
        title: str,
        instruction: str,
        model: str,
        target_dir: str,
        scope_text: str,
    ) -> dict[str, object]:
        """Generate a safe note draft proposal."""
        draft = self._drafts.draft_note(
            title=title.strip(),
            instruction=instruction.strip(),
            model=model.strip(),
            target_dir=target_dir.strip() or None,
            scope_dirs=parse_scope_dirs(scope_text),
        )
        return serialize_generated_note_draft(draft)

    def analyze_directory(self, *, directory: str) -> dict[str, object]:
        """Analyze a whole vault directory and return a JSON-friendly report."""
        report = self._directory_analysis.analyze_directory(directory.strip())
        return serialize_directory_analysis_report(report)

    def auto_route(
        self,
        *,
        prompt: str,
        title: str = "",
        directory: str = "",
        target_dir: str = "",
    ) -> dict[str, object]:
        """Return the backend routing decision for one request."""
        decision = self._router.route_request(
            prompt=prompt.strip(),
            title=title.strip(),
            directory=directory.strip(),
            target_dir=target_dir.strip(),
        )
        return serialize_route_decision(decision)

    def auto_run(
        self,
        *,
        prompt: str,
        model: str,
        scope_text: str,
        title: str = "",
        directory: str = "",
        target_dir: str = "",
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "auto",
        discussion_preset: str | None = None,
    ) -> dict[str, object]:
        """Route the request automatically and execute the selected workflow."""
        decision = self._router.route_request(
            prompt=prompt.strip(),
            title=title.strip(),
            directory=directory.strip(),
            target_dir=target_dir.strip(),
        )
        route_payload = serialize_route_decision(decision)
        effective_reasoning_mode = (
            decision.reasoning_mode if reasoning_mode == "auto" else normalize_reasoning_mode(reasoning_mode)
        )
        if decision.workflow == "agent":
            result = self.run_agent(
                request_text=prompt,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
                discussion_preset=discussion_preset,
            )
        elif decision.workflow == "implementation":
            result = self.scope_implementation(
                request_text=prompt,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
            )
        elif decision.workflow == "draft":
            result = self.draft_note(
                title=decision.derived_title or title or "Draft Note",
                instruction=prompt,
                model=model,
                target_dir=target_dir or "Inbox",
                scope_text=scope_text,
            )
        elif decision.workflow == "analyze":
            resolved_directory = decision.derived_directory or directory
            if not resolved_directory:
                raise ValueError(
                    "Auto-routing selected directory analysis but no directory could be inferred."
                )
            result = self.analyze_directory(directory=resolved_directory)
        else:
            result = self.ask(
                question=prompt,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
            )
        return {
            "route": route_payload,
            "reasoning_mode": effective_reasoning_mode,
            "result": result,
        }

    def list_ask_history(self, *, limit: int) -> list[dict[str, object]]:
        """Return recent grounded ask/scope history entries."""
        return [
            serialize_query_history_entry(entry)
            for entry in self._history_repository.list_entries(limit=limit)
        ]

    def list_agent_history(self, *, limit: int) -> list[dict[str, object]]:
        """Return recent persisted agent-runtime history entries."""
        return [
            serialize_agent_run_history_entry(entry)
            for entry in self._history_repository.list_agent_runs(limit=limit)
        ]

    def history_overview(self) -> dict[str, int]:
        """Return per-stream history counts for the UI."""
        return {
            "ask": self._history_repository.count_entries(),
            "agent": self._history_repository.count_agent_runs(),
            "benchmark": self._history_repository.count_benchmark_runs(),
        }

    def list_models(self) -> list[str]:
        """Return locally available Ollama model names."""
        return self._ollama_client.list_models()

    def update_agent_task_plan(
        self,
        *,
        entry_id: int,
        task_plan: dict[str, object],
    ) -> dict[str, object]:
        """Persist one task-plan update for a saved agent runtime entry."""
        updated = self._history_repository.update_agent_runtime_task_plan(
            entry_id=entry_id,
            task_plan_payload=task_plan,
        )
        if updated is None or updated.artifact_payload is None:
            raise ValueError(f"Agent history entry not found: {entry_id}")
        return updated.artifact_payload

    def frontend_dist_dir(self) -> Path:
        """Return the configured frontend distribution directory."""
        return self._frontend_dist_dir

    def frontend_index_path(self) -> Path:
        """Return the expected React entrypoint HTML path."""
        return self._frontend_dist_dir / "index.html"

    def has_frontend_assets(self) -> bool:
        """Return whether the built JS frontend is available."""
        return self.frontend_index_path().exists()

    def resolve_frontend_asset(self, request_path: str) -> Path:
        """Resolve a frontend asset path inside the built distribution directory."""
        cleaned = request_path.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
        relative = cleaned.lstrip("/") or "index.html"
        candidate = (self._frontend_dist_dir / relative).resolve()
        root = self._frontend_dist_dir.resolve()
        if root == candidate or root in candidate.parents:
            return candidate
        return root / "index.html"

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the web UI."""
    parser = argparse.ArgumentParser(description="Run the PersonalAI local web UI.")
    parser.add_argument("--vault", type=Path, required=True, help="Path to the Obsidian vault root.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind.")
    parser.add_argument(
        "--ollama-base-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help="Base URL for the local Ollama server.",
    )
    parser.add_argument(
        "--ollama-timeout-seconds",
        type=int,
        help="Optional timeout for Ollama HTTP calls in seconds. Overrides OLLAMA_TIMEOUT_SECONDS.",
    )
    parser.add_argument(
        "--frontend-dist-dir",
        type=Path,
        default=DEFAULT_FRONTEND_DIST_DIR,
        help="Path to the built frontend dist directory served for the JS UI.",
    )
    return parser


def make_handler(app: PersonalAIWebApp):
    """Create a request handler bound to the app instance."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                status_code, payload = handle_api_request(
                    app,
                    method="GET",
                    path=self.path,
                    body=None,
                )
                self._send_json(payload, status_code=status_code)
                return
            self._send_frontend()

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            if self.path.startswith("/api/"):
                status_code, payload = handle_api_request(
                    app,
                    method="POST",
                    path=self.path,
                    body=body,
                )
                self._send_json(payload, status_code=status_code)
                return
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Use the JSON API for mutations.")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_json(self, payload: dict[str, object] | list[object], *, status_code: int) -> None:
            encoded = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_frontend(self) -> None:
            if not app.has_frontend_assets():
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                message = (
                    "Frontend build not found. Run `npm run build` inside "
                    "`Projects/PersonalAI/personal_ai_mvp/frontend`."
                )
                encoded = message.encode("utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            requested_path = app.resolve_frontend_asset(self.path)
            is_existing_asset = requested_path.exists() and requested_path.is_file()
            response_path = requested_path if is_existing_asset else app.frontend_index_path()
            content_type = mimetypes.guess_type(response_path.name)[0] or "application/octet-stream"
            if response_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            encoded = response_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


def handle_api_request(
    app: PersonalAIWebApp,
    *,
    method: str,
    path: str,
    body: str | None,
) -> tuple[int, dict[str, object] | list[object]]:
    """Handle JSON API requests for the future JS frontend."""
    return _handle_api_request(
        app,
        method=method,
        path=path,
        body=body,
        default_ui_model=DEFAULT_UI_MODEL,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the local web UI server."""
    args = build_parser().parse_args(argv)
    app = PersonalAIWebApp(
        vault_root=args.vault,
        ollama_base_url=args.ollama_base_url,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
        frontend_dist_dir=args.frontend_dist_dir,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"PersonalAI UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

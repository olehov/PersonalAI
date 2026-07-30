"""Route dispatch for the PersonalAI web JSON API."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from web_app.api_helpers import (
    normalize_reasoning_mode,
    parse_conversation_history,
)

LOGGER = logging.getLogger(__name__)


def _ensure_execution_payload(
    result: dict[str, object],
    *,
    requested_workflow: str,
    executed_workflow: str,
    requested_model: str = "",
    reasoning_mode: str | None = None,
) -> dict[str, object]:
    """Backfill execution debug metadata when the lower layer omitted it."""
    if isinstance(result.get("execution"), dict):
        return result
    resolved_model = str(result.get("model", "")).strip() or None
    return {
        **result,
        "execution": {
            "requested_workflow": requested_workflow,
            "executed_workflow": executed_workflow,
            "route_workflow": None,
            "requested_model": requested_model.strip() or None,
            "resolved_model": resolved_model,
            "reasoning_mode": reasoning_mode,
        },
    }


def handle_api_request(
    app,
    *,
    method: str,
    path: str,
    body: str | None,
    default_ui_model: str,
    debug_api_errors: bool = False,
) -> tuple[int, dict[str, object] | list[object]]:
    """Handle JSON API requests for the web frontend."""
    parsed = urlparse(path)
    route = parsed.path.rstrip("/")

    try:
        if method == "GET" and route == "/api/ask-history":
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            return HTTPStatus.OK, {
                "history_kind": "ask",
                "entries": app.list_ask_history(limit=limit),
            }

        if method == "GET" and route == "/api/agent-history":
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            return HTTPStatus.OK, {
                "history_kind": "agent",
                "entries": app.list_agent_history(limit=limit),
            }

        if method == "GET" and route == "/api/benchmark-history":
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            return HTTPStatus.OK, {
                "history_kind": "benchmark",
                "entries": app.list_benchmark_history(limit=limit),
            }

        if method == "GET" and route == "/api/history-overview":
            return HTTPStatus.OK, {
                "streams": app.history_overview(),
            }

        if method == "GET" and route == "/api/history":
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            return HTTPStatus.OK, {
                "history_kind": "ask",
                "deprecated": True,
                "entries": app.list_ask_history(limit=limit),
            }

        if method == "GET" and route == "/api/models":
            return HTTPStatus.OK, {
                "models": app.list_models(),
                "default_model": default_ui_model,
            }

        if method == "GET" and route == "/api/health":
            return HTTPStatus.OK, app.health_status()

        if method == "POST" and route == "/api/reload":
            app.reload()
            return HTTPStatus.OK, {
                "status": "ok",
                "message": "Vault index reloaded.",
            }

        if method != "POST":
            return HTTPStatus.METHOD_NOT_ALLOWED, {
                "error": f"Unsupported method for {route}: {method}",
            }

        payload = json.loads(body or "{}")

        if route == "/api/ask":
            question = str(payload.get("question", "")).strip()
            if not question:
                raise ValueError("Question is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            reasoning_mode = normalize_reasoning_mode(payload.get("reasoning_mode"))
            result = app.ask(
                question=question,
                model=str(payload.get("model", "")),
                scope_text=str(payload.get("scope_text", "")),
                conversation_history=conversation_history,
                reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
            )
            return HTTPStatus.OK, {
                "result": _ensure_execution_payload(
                    result,
                    requested_workflow="ask",
                    executed_workflow="ask",
                    requested_model=str(payload.get("model", "")),
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                )
            }

        if route == "/api/auto-route":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                raise ValueError("Prompt is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            route_payload = app.auto_route(
                prompt=prompt,
                conversation_history=conversation_history,
                title=str(payload.get("title", "")),
                directory=str(payload.get("directory", "")),
                target_dir=str(payload.get("target_dir", "")),
            )
            return HTTPStatus.OK, {
                "route": route_payload["decision"],
                "preprocess": route_payload["preprocess"],
            }

        if route == "/api/auto-run":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                raise ValueError("Prompt is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            return HTTPStatus.OK, app.auto_run(
                prompt=prompt,
                model=str(payload.get("model", "")),
                scope_text=str(payload.get("scope_text", "")),
                title=str(payload.get("title", "")),
                directory=str(payload.get("directory", "")),
                target_dir=str(payload.get("target_dir", "Inbox")),
                conversation_history=conversation_history,
                reasoning_mode=normalize_reasoning_mode(payload.get("reasoning_mode", "auto")),
                discussion_preset=str(payload.get("discussion_preset", "")).strip() or None,
            )

        if route == "/api/implementation-scope":
            request_text = str(payload.get("request_text", "")).strip()
            if not request_text:
                raise ValueError("Implementation request is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            reasoning_mode = normalize_reasoning_mode(payload.get("reasoning_mode"))
            result = app.scope_implementation(
                request_text=request_text,
                model=str(payload.get("model", "")),
                scope_text=str(payload.get("scope_text", "")),
                conversation_history=conversation_history,
                reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
            )
            return HTTPStatus.OK, {
                "result": _ensure_execution_payload(
                    result,
                    requested_workflow="implementation",
                    executed_workflow="implementation",
                    requested_model=str(payload.get("model", "")),
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                )
            }

        if route == "/api/agent-runtime":
            request_text = str(payload.get("request_text", "")).strip()
            if not request_text:
                raise ValueError("Agent runtime request is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            reasoning_mode = normalize_reasoning_mode(payload.get("reasoning_mode"))
            result = app.run_agent(
                request_text=request_text,
                model=str(payload.get("model", "")),
                scope_text=str(payload.get("scope_text", "")),
                conversation_history=conversation_history,
                reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                discussion_preset=str(payload.get("discussion_preset", "")).strip() or None,
            )
            return HTTPStatus.OK, {
                "result": _ensure_execution_payload(
                    result,
                    requested_workflow="agent",
                    executed_workflow="agent",
                    requested_model=str(payload.get("model", "")),
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                )
            }

        if route == "/api/agent-task-plan":
            entry_id = int(payload.get("entry_id", 0))
            task_plan = payload.get("task_plan")
            if entry_id <= 0:
                raise ValueError("A valid agent history entry id is required.")
            if not isinstance(task_plan, dict):
                raise ValueError("Task plan payload is required.")
            return HTTPStatus.OK, {
                "result": app.update_agent_task_plan(
                    entry_id=entry_id,
                    task_plan=task_plan,
                )
            }

        if route == "/api/analyze-dir":
            directory = str(payload.get("directory", "")).strip()
            if not directory:
                raise ValueError("Directory is required.")
            result = app.analyze_directory(directory=directory)
            return HTTPStatus.OK, {
                "result": _ensure_execution_payload(
                    result,
                    requested_workflow="analyze",
                    executed_workflow="analyze",
                ),
            }

        if route == "/api/draft-note":
            title = str(payload.get("title", "")).strip()
            instruction = str(payload.get("instruction", "")).strip()
            if not title:
                raise ValueError("Draft title is required.")
            if not instruction:
                raise ValueError("Draft instruction is required.")
            result = app.draft_note(
                title=title,
                instruction=instruction,
                model=str(payload.get("model", "")),
                target_dir=str(payload.get("target_dir", "Inbox")),
                scope_text=str(payload.get("scope_text", "")),
            )
            return HTTPStatus.OK, {
                "result": _ensure_execution_payload(
                    result,
                    requested_workflow="draft",
                    executed_workflow="draft",
                    requested_model=str(payload.get("model", "")),
                )
            }

        return HTTPStatus.NOT_FOUND, {
            "error": f"Unknown API route: {route}",
        }
    except json.JSONDecodeError:
        return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."}
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Unhandled API error for %s %s", method, route or path, exc_info=exc)
        if debug_api_errors:
            return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error."}

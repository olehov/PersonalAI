"""JSON API helpers for the local PersonalAI web UI."""

from __future__ import annotations

import json
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from personal_ai.domain.models import PromptMessage


def parse_scope_dirs(raw_value: str) -> tuple[str, ...]:
    """Parse comma- or newline-separated scope directories."""
    pieces = [
        chunk.strip()
        for line in raw_value.replace("\r", "\n").split("\n")
        for chunk in line.split(",")
    ]
    cleaned: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        if not piece:
            continue
        key = piece.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(piece)
    return tuple(cleaned)


def parse_conversation_history(raw_value: object) -> tuple[PromptMessage, ...]:
    """Parse compact chat history payloads sent by the frontend."""
    if not isinstance(raw_value, list):
        return ()

    history: list[PromptMessage] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        history.append(PromptMessage(role=role, content=content))
    return tuple(history)


def normalize_reasoning_mode(raw_value: object) -> str:
    """Normalize the requested reasoning mode."""
    normalized = str(raw_value or "").strip().lower()
    if normalized == "high":
        return "high"
    if normalized == "auto":
        return "auto"
    return "standard"


def serialize_route_decision(decision) -> dict[str, object]:
    """Convert a route decision to a JSON-friendly payload."""
    return {
        "workflow": decision.workflow,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "reasoning_mode": decision.reasoning_mode,
        "derived_title": decision.derived_title,
        "derived_directory": decision.derived_directory,
    }


def handle_api_request(
    app,
    *,
    method: str,
    path: str,
    body: str | None,
    default_ui_model: str,
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
            return HTTPStatus.OK, {
                "result": app.ask(
                    question=question,
                    model=str(payload.get("model", default_ui_model)),
                    scope_text=str(payload.get("scope_text", "")),
                    conversation_history=conversation_history,
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                )
            }

        if route == "/api/auto-route":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                raise ValueError("Prompt is required.")
            return HTTPStatus.OK, {
                "route": app.auto_route(
                    prompt=prompt,
                    title=str(payload.get("title", "")),
                    directory=str(payload.get("directory", "")),
                    target_dir=str(payload.get("target_dir", "")),
                )
            }

        if route == "/api/auto-run":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                raise ValueError("Prompt is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            return HTTPStatus.OK, app.auto_run(
                prompt=prompt,
                model=str(payload.get("model", default_ui_model)),
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
            return HTTPStatus.OK, {
                "result": app.scope_implementation(
                    request_text=request_text,
                    model=str(payload.get("model", default_ui_model)),
                    scope_text=str(payload.get("scope_text", "")),
                    conversation_history=conversation_history,
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                )
            }

        if route == "/api/agent-runtime":
            request_text = str(payload.get("request_text", "")).strip()
            if not request_text:
                raise ValueError("Agent runtime request is required.")
            conversation_history = parse_conversation_history(payload.get("chat_history"))
            reasoning_mode = normalize_reasoning_mode(payload.get("reasoning_mode"))
            return HTTPStatus.OK, {
                "result": app.run_agent(
                    request_text=request_text,
                    model=str(payload.get("model", default_ui_model)),
                    scope_text=str(payload.get("scope_text", "")),
                    conversation_history=conversation_history,
                    reasoning_mode="high" if reasoning_mode == "auto" else reasoning_mode,
                    discussion_preset=str(payload.get("discussion_preset", "")).strip() or None,
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
            return HTTPStatus.OK, {
                "result": app.analyze_directory(directory=directory),
            }

        if route == "/api/draft-note":
            title = str(payload.get("title", "")).strip()
            instruction = str(payload.get("instruction", "")).strip()
            if not title:
                raise ValueError("Draft title is required.")
            if not instruction:
                raise ValueError("Draft instruction is required.")
            return HTTPStatus.OK, {
                "result": app.draft_note(
                    title=title,
                    instruction=instruction,
                    model=str(payload.get("model", default_ui_model)),
                    target_dir=str(payload.get("target_dir", "Inbox")),
                    scope_text=str(payload.get("scope_text", "")),
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
        return HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}

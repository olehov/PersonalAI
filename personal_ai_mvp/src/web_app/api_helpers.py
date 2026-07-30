"""Helper functions for the PersonalAI web JSON API."""

from __future__ import annotations

from domain.models import PromptMessage


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
        "web_search_required": decision.web_search_required,
        "web_search_reason": decision.web_search_reason,
    }

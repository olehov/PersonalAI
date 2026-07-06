"""Conversation-history helpers for the chat service."""

from __future__ import annotations

from personal_ai.domain.models import PromptMessage


def compact_history_content(content: str, *, max_history_chars_per_message: int) -> str:
    """Trim oversized history turns so follow-up prompts stay focused."""
    stripped = content.strip()
    if not stripped:
        return ""
    if len(stripped) <= max_history_chars_per_message:
        return stripped
    return stripped[: max_history_chars_per_message - 3].rstrip() + "..."


def normalize_conversation_history(
    conversation_history: tuple[PromptMessage, ...],
    *,
    max_history_turns: int,
    max_history_chars_per_message: int,
) -> tuple[PromptMessage, ...]:
    """Keep only recent user/assistant turns and trim their size."""
    normalized: list[PromptMessage] = []
    for message in conversation_history:
        role = message.role.strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = compact_history_content(
            message.content,
            max_history_chars_per_message=max_history_chars_per_message,
        )
        if not content:
            continue
        normalized.append(PromptMessage(role=role, content=content))

    if not normalized:
        return ()

    return tuple(normalized[-max_history_turns:])


def merge_conversation_history(
    base_messages: tuple[PromptMessage, ...],
    conversation_history: tuple[PromptMessage, ...],
    *,
    max_history_turns: int,
    max_history_chars_per_message: int,
) -> tuple[PromptMessage, ...]:
    """Insert recent user/assistant chat history before the current task prompt."""
    if len(base_messages) < 2:
        return base_messages

    normalized_history = normalize_conversation_history(
        conversation_history,
        max_history_turns=max_history_turns,
        max_history_chars_per_message=max_history_chars_per_message,
    )
    if not normalized_history:
        return base_messages

    return (
        base_messages[0],
        *normalized_history,
        *base_messages[1:],
    )

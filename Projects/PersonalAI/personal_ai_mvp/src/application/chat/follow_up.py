"""Shared follow-up detection and unfinished-answer recovery helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re

from application.chat.query_mapping import normalize_knowledge_query
from domain.models import PromptMessage


_FOLLOW_UP_HINTS = (
    "continue",
    "continue from there",
    "continue from here",
    "finish it",
    "finish this",
    "finish the task",
    "finish the code",
    "complete it",
    "complete this",
    "complete everything",
    "complete the task",
    "you stopped",
    "you did not complete",
    "you didn't finish",
    "you did not finish",
    "not finished",
    "not complete",
    "keep going",
    "keep writing",
    "go on",
    "resume",
    "resume from there",
    "do not restart",
    "don't restart",
    "pick up where you left off",
    "продовжуй",
    "допиши",
    "не завершив",
    "не закінчив",
    "заверши",
)
_SHORT_FOLLOW_UP_PROMPTS = {
    "more",
    "continue it",
    "finish",
    "complete",
    "go on",
    "resume",
    "продовжуй",
    "допиши",
    "ще",
}
_UNFINISHED_COMPLAINT_HINTS = (
    "you stopped",
    "you did not complete",
    "you didn't finish",
    "you did not finish",
    "not finished",
    "not complete",
    "unfinished",
    "incomplete",
    "не завершив",
    "не закінчив",
)
_IMPLEMENTATION_SECTIONS = (
    "architecture",
    "modules",
    "execution flow",
    "edge cases",
    "code skeleton",
)
_TRAILING_INCOMPLETE_PATTERN = re.compile(
    r"(?:[=,([{:+\-/*]|->|&&|\|\|)\s*$|"
    r"\b(?:return|if|for|while|switch|case|struct|typedef)\s*$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FollowUpContext:
    """Derived follow-up metadata for one request."""

    is_follow_up: bool = False
    anchor_question: str | None = None
    previous_assistant_answer: str | None = None
    should_recover_unfinished_answer: bool = False


def build_follow_up_context(
    prompt: str,
    conversation_history: tuple[PromptMessage, ...],
) -> FollowUpContext:
    """Resolve whether the prompt is a follow-up and if unfinished recovery should apply."""
    normalized_prompt = normalize_knowledge_query(prompt)
    collapsed_prompt = " ".join(normalized_prompt.strip().split()).casefold()
    is_follow_up = is_follow_up_prompt(collapsed_prompt)
    if not is_follow_up or not conversation_history:
        return FollowUpContext()

    anchor_question = find_follow_up_anchor(conversation_history)
    previous_assistant_answer = find_latest_assistant_answer(conversation_history)
    should_recover = False
    if previous_assistant_answer:
        should_recover = (
            _mentions_unfinished_complaint(collapsed_prompt)
            or looks_like_incomplete_answer(previous_assistant_answer)
        )
    return FollowUpContext(
        is_follow_up=is_follow_up,
        anchor_question=anchor_question,
        previous_assistant_answer=previous_assistant_answer,
        should_recover_unfinished_answer=should_recover,
    )


def is_follow_up_prompt(normalized_prompt: str) -> bool:
    """Return True when the prompt looks like a continuation request."""
    if any(hint in normalized_prompt for hint in _FOLLOW_UP_HINTS):
        return True
    short_prompt = normalized_prompt.strip(" .:-!?")
    return short_prompt in _SHORT_FOLLOW_UP_PROMPTS


def looks_like_follow_up_with_history(
    prompt: str,
    conversation_history: tuple[PromptMessage, ...],
) -> bool:
    """Return True when a short prompt should be anchored to the prior unfinished task."""
    normalized_prompt = normalize_knowledge_query(prompt)
    collapsed_prompt = " ".join(normalized_prompt.strip().split()).casefold()
    if is_follow_up_prompt(collapsed_prompt):
        return True
    if not conversation_history or not collapsed_prompt:
        return False

    latest_assistant_answer = find_latest_assistant_answer(conversation_history)
    if not latest_assistant_answer or not looks_like_incomplete_answer(latest_assistant_answer):
        return False

    word_count = len(collapsed_prompt.split())
    if word_count > 20 or len(collapsed_prompt) > 160:
        return False

    continuation_tokens = (
        "finish",
        "complete",
        "continue",
        "resume",
        "stopped",
        "unfinished",
        "incomplete",
        "more",
        "допиши",
        "продовжуй",
        "заверши",
        "не завершив",
        "не закінчив",
    )
    if any(token in collapsed_prompt for token in continuation_tokens):
        return True

    return word_count <= 6


def find_follow_up_anchor(
    conversation_history: tuple[PromptMessage, ...],
) -> str | None:
    """Find the most recent substantive user task before the current follow-up."""
    for message in reversed(conversation_history):
        if message.role.strip().lower() != "user":
            continue
        normalized = normalize_knowledge_query(message.content)
        collapsed = " ".join(normalized.strip().split()).casefold()
        if not collapsed or is_follow_up_prompt(collapsed):
            continue
        return message.content.strip()
    return None


def find_latest_assistant_answer(
    conversation_history: tuple[PromptMessage, ...],
) -> str | None:
    """Return the latest assistant turn from the recent chat history."""
    for message in reversed(conversation_history):
        if message.role.strip().lower() == "assistant" and message.content.strip():
            return message.content.strip()
    return None


def looks_like_incomplete_answer(answer_text: str) -> bool:
    """Heuristically detect obviously cut-off assistant answers."""
    stripped = answer_text.strip()
    if not stripped:
        return False

    if stripped.count("```") % 2 == 1:
        return True

    lowered = stripped.casefold()
    present_sections = [
        section for section in _IMPLEMENTATION_SECTIONS if section in lowered
    ]
    if 0 < len(present_sections) < len(_IMPLEMENTATION_SECTIONS):
        return True

    last_line = stripped.splitlines()[-1].strip()
    if not last_line:
        return False
    if re.fullmatch(r"(?:[-*]|\d+\.)", last_line):
        return True
    if _TRAILING_INCOMPLETE_PATTERN.search(last_line):
        return True
    if last_line != "```" and last_line.endswith(("`", ":", "-", "–", "—", "(", "[", "{", ",")):
        return True
    return False


def build_unfinished_recovery_instruction(
    *,
    follow_up_prompt: str,
    previous_assistant_answer: str,
) -> str:
    """Build an instruction block that tells the model to finish the prior draft."""
    excerpt = previous_assistant_answer.strip()
    if len(excerpt) > 900:
        excerpt = excerpt[:897].rstrip() + "..."
    return (
        "Follow-up Recovery:\n"
        "- The previous assistant answer was unfinished.\n"
        "- Continue the same task from the prior answer instead of restarting from scratch.\n"
        "- The original task context and the prior draft excerpt are already provided below.\n"
        "- Do not claim that the draft, task, or context is missing.\n"
        "- Do not ask the user to resend the previous draft before continuing.\n"
        "- Recover any partially written file, function, list, or code block and finish it cleanly.\n"
        "- If the previous answer was cut off mid-code, restart from the nearest safe boundary and complete that block.\n"
        "- Return one completed answer that resolves the unfinished work.\n"
        f"- User follow-up request: {follow_up_prompt.strip()}\n"
        "Previous Assistant Draft Excerpt:\n"
        f"{excerpt}"
    )


def _mentions_unfinished_complaint(normalized_prompt: str) -> bool:
    return any(hint in normalized_prompt for hint in _UNFINISHED_COMPLAINT_HINTS)

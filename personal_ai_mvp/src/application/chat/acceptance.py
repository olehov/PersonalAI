"""Acceptance checks for implementation-oriented chat answers."""

from __future__ import annotations

from dataclasses import dataclass
import re

from domain.models import PromptMessage


_SECTION_NAMES = (
    "Architecture",
    "Modules",
    "Execution Flow",
    "Edge Cases",
    "Code Skeleton",
)
_TRAILING_INCOMPLETE_PATTERN = re.compile(
    r"(?:[=,([{:+\-/*]|->|&&|\|\|)\s*$|"
    r"\b(?:return|if|for|while|switch|case|struct|typedef|static|int|char|void)\s*$",
    flags=re.IGNORECASE,
)
_ABRUPT_ENDING_PATTERN = re.compile(r"(?:[:([{,]|[-–—]\s*|`)\s*$")
_NOISE_PATTERNS = (
    "personalai frontend",
    "reload vault",
    "history",
    "draft note",
    "analyze directory",
    "local-first developer assistant",
)
_FOLLOW_UP_RECOVERY_MARKER = "follow-up recovery:"
_MISSING_CONTEXT_REFUSAL_PATTERNS = (
    "i don't have enough detail",
    "i do not have enough detail",
    "i don't have the original draft",
    "i do not have the original draft",
    "i need the following from you",
    "once you provide those details",
    "if you provide those details",
    "i need the full draft",
    "i need the original draft",
    "please provide the previous draft",
    "resend the previous draft",
)
_META_REPAIR_LEAKAGE_PATTERNS = (
    "the user wants",
    "the user asked",
    "we need to repair",
    "we need to finish",
    "we need to complete",
    "we need to respond",
    "let's produce final answer",
    "let's provide",
    "we can provide",
    "we should not invent",
    "we must ensure code compiles",
    "the previous answer had an unfinished code block",
    "we must close all braces",
    "also need architecture, modules, execution flow, edge cases sections",
)
_META_REPAIR_LEADING_PATTERNS = (
    r"^\s*we need to\b",
    r"^\s*let'?s\b",
    r"^\s*the draft\b",
    r"^\s*the previous draft\b",
    r"^\s*the previous answer\b",
    r"^\s*but earlier\b",
    r"^\s*also need\b",
    r"^\s*we must\b",
    r"^\s*we should\b",
)
_EXPLICIT_CODE_REQUEST_PATTERNS = (
    "generate code",
    "full implementation",
    "complete implementation",
    "code skeleton",
    "compile-ready",
    "standalone program",
    "single-file c program",
)


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    """Outcome of validating one generated answer."""

    passed: bool
    issues: tuple[str, ...] = ()


def assess_answer_quality(
    *,
    answer_text: str,
    task_mode: str,
    base_messages: tuple[PromptMessage, ...],
) -> AcceptanceResult:
    """Assess whether a generated answer is complete enough to return."""
    if task_mode != "implementation":
        return AcceptanceResult(passed=True)

    stripped = answer_text.strip()
    if not stripped:
        return AcceptanceResult(
            passed=False,
            issues=("The answer is empty.",),
        )

    issues: list[str] = []
    lowered = stripped.casefold()

    if stripped.count("```") % 2 == 1:
        issues.append("A fenced code block is left open.")
    elif stripped.count("`") % 2 == 1:
        issues.append("Inline or fenced code is left open.")

    missing_sections = [
        section for section in _SECTION_NAMES if section.casefold() not in lowered
    ]
    if missing_sections:
        issues.append(
            "The implementation response contract is incomplete. Missing sections: "
            + ", ".join(missing_sections)
            + "."
        )

    last_line = stripped.splitlines()[-1].strip()
    if re.fullmatch(r"(?:[-*]|\d+\.)", last_line):
        issues.append("The answer ends in the middle of a list.")
    elif _TRAILING_INCOMPLETE_PATTERN.search(last_line):
        issues.append("The answer appears to end mid-function or mid-statement.")
    elif last_line != "```" and _ABRUPT_ENDING_PATTERN.search(last_line):
        issues.append("The answer appears to stop abruptly before finishing the current section.")

    topic_drift_issue = _detect_topic_drift(
        answer_text=stripped,
        base_messages=base_messages,
    )
    if topic_drift_issue is not None:
        issues.append(topic_drift_issue)

    missing_context_issue = _detect_missing_context_refusal(
        answer_text=stripped,
        base_messages=base_messages,
    )
    if missing_context_issue is not None:
        issues.append(missing_context_issue)

    meta_repair_issue = _detect_meta_repair_leakage(answer_text=stripped)
    if meta_repair_issue is not None:
        issues.append(meta_repair_issue)

    missing_code_issue = _detect_missing_code_for_explicit_code_request(
        answer_text=stripped,
        base_messages=base_messages,
    )
    if missing_code_issue is not None:
        issues.append(missing_code_issue)

    return AcceptanceResult(
        passed=not issues,
        issues=tuple(issues),
    )


def build_repair_messages(
    *,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
    issues: tuple[str, ...],
) -> tuple[PromptMessage, ...]:
    """Build one bounded repair pass for a weak implementation answer."""
    issue_lines = "\n".join(f"- {issue}" for issue in issues)
    repair_prompt = (
        "Implementation Answer Repair Pass:\n"
        "- The previous draft failed acceptance checks for an implementation answer.\n"
        "- Repair the answer so it fully satisfies the original grounded request.\n"
        "- Keep the response grounded in the retrieved context and do not invent files, results, or validation you do not have.\n"
        "- Finish incomplete code blocks, incomplete sections, and incomplete lists.\n"
        "- Remove topic drift and keep the answer centered on the requested implementation task.\n"
        "- Return only the repaired final answer.\n\n"
        "Acceptance Issues:\n"
        f"{issue_lines}\n\n"
        f"Draft To Repair:\n{draft_text}"
    )
    return (
        *base_messages,
        PromptMessage(role="assistant", content=draft_text),
        PromptMessage(role="user", content=repair_prompt),
    )


def _detect_topic_drift(
    *,
    answer_text: str,
    base_messages: tuple[PromptMessage, ...],
) -> str | None:
    user_prompt = next(
        (message.content for message in reversed(base_messages) if message.role == "user"),
        "",
    )
    focus_entities = _extract_focus_entities(user_prompt)
    if not focus_entities:
        return None

    answer_tokens = _tokenize(answer_text)
    if focus_entities & answer_tokens:
        return None

    lowered = answer_text.casefold()
    if any(pattern in lowered for pattern in _NOISE_PATTERNS):
        return (
            "The answer drifted into unrelated UI or product text instead of the requested implementation task."
        )

    if "```" not in answer_text and len(answer_tokens & _implementation_anchor_tokens()) < 3:
        return (
            "The answer drifted away from concrete implementation details and no longer stays focused on the requested coding task."
        )
    return None


def _detect_missing_context_refusal(
    *,
    answer_text: str,
    base_messages: tuple[PromptMessage, ...],
) -> str | None:
    user_prompt = next(
        (message.content for message in reversed(base_messages) if message.role == "user"),
        "",
    )
    if _FOLLOW_UP_RECOVERY_MARKER not in user_prompt.casefold():
        return None

    lowered = answer_text.casefold()
    if any(pattern in lowered for pattern in _MISSING_CONTEXT_REFUSAL_PATTERNS):
        return (
            "The answer incorrectly claims that the previous draft or task context is missing even though follow-up recovery already supplied it."
        )
    return None


def _detect_meta_repair_leakage(*, answer_text: str) -> str | None:
    lowered = answer_text.casefold()
    if any(pattern in lowered for pattern in _META_REPAIR_LEAKAGE_PATTERNS):
        return (
            "The answer leaked internal repair or planning commentary instead of returning only the final implementation answer."
        )
    opening_excerpt = "\n".join(answer_text.strip().splitlines()[:4]).casefold()
    if any(re.search(pattern, opening_excerpt, flags=re.IGNORECASE) for pattern in _META_REPAIR_LEADING_PATTERNS):
        return (
            "The answer starts with internal repair or review commentary instead of the final implementation answer."
        )
    return None


def _detect_missing_code_for_explicit_code_request(
    *,
    answer_text: str,
    base_messages: tuple[PromptMessage, ...],
) -> str | None:
    user_prompt = next(
        (message.content for message in reversed(base_messages) if message.role == "user"),
        "",
    )
    lowered_prompt = user_prompt.casefold()
    if not any(pattern in lowered_prompt for pattern in _EXPLICIT_CODE_REQUEST_PATTERNS):
        return None

    if "```" in answer_text:
        return None

    if re.search(r"\b[a-z0-9_]+\.(?:c|h|cpp|hpp|py|js|ts|java|go|rs)\b", answer_text, flags=re.IGNORECASE):
        return None

    if re.search(
        r"\b(?:int|void|char|float|double|size_t|struct)\s+\**[A-Za-z_][A-Za-z0-9_]*\s*\(",
        answer_text,
    ):
        return None

    return (
        "The request explicitly asked for code generation, but the answer does not include concrete code or a file-by-file skeleton."
    )


def _extract_focus_entities(user_prompt: str) -> set[str]:
    tokens = _tokenize(user_prompt)
    ignore = _implementation_anchor_tokens() | {
        "task",
        "request",
        "question",
        "focus",
        "answer",
        "reasoning",
        "mode",
        "primary",
        "related",
        "notes",
        "grounded",
        "context",
    }
    entities = {token for token in tokens if token not in ignore and len(token) >= 3}
    for explicit in ("bsq", "minishell"):
        if explicit in user_prompt.casefold():
            entities.add(explicit)
    return entities


def _implementation_anchor_tokens() -> set[str]:
    return {
        "architecture",
        "modules",
        "execution",
        "flow",
        "edge",
        "cases",
        "code",
        "skeleton",
        "parser",
        "executor",
        "function",
        "functions",
        "module",
        "implementation",
        "program",
        "file",
        "files",
        "header",
        "headers",
        "struct",
        "cleanup",
        "validation",
    }


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_]{2,}", text.casefold()))

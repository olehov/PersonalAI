"""Recursive-answer generation helpers for the chat service."""

from __future__ import annotations

from application.chat.acceptance import (
    assess_answer_quality,
    build_repair_messages,
)
from application.chat.model_options import (
    answer_generation_options,
    critique_generation_options,
    repair_generation_options,
    refinement_generation_options,
)
from domain.models import PromptMessage


def build_critique_messages(
    *,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
) -> tuple[PromptMessage, ...]:
    """Ask the model to audit its first draft against the grounded prompt."""
    critique_prompt = (
        "Recursive Refinement Critique:\n"
        "- Review the earlier draft against the grounded prompt and cited context.\n"
        "- Identify only concrete weaknesses that matter for correctness, grounding, or coding usefulness.\n"
        "- Focus on unsupported claims, missing implementation detail, weak file/function specificity, and off-topic generalization.\n"
        "- Return exactly these sections in this order: Strengths, Issues, Missing Grounding, Improve.\n"
        "- Keep it compact and actionable.\n\n"
        f"Draft To Critique:\n{draft_text}"
    )
    return (
        *base_messages,
        PromptMessage(role="assistant", content=draft_text),
        PromptMessage(role="user", content=critique_prompt),
    )


def build_refinement_messages(
    *,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
    critique_text: str,
) -> tuple[PromptMessage, ...]:
    """Ask the model to produce a corrected final answer from the critique."""
    refinement_prompt = (
        "Recursive Refinement Final Pass:\n"
        "- Rewrite the answer using the critique.\n"
        "- Keep the final answer grounded in the retrieved notes and current request.\n"
        "- Prefer precise coding guidance, concrete modules, functions, files, and validation steps over generic advice.\n"
        "- Remove unsupported claims and invented paths, files, or results.\n"
        "- Return only the improved final answer, not the critique.\n\n"
        f"Initial Draft:\n{draft_text}\n\n"
        f"Critique:\n{critique_text}"
    )
    return (
        *base_messages,
        PromptMessage(role="assistant", content=draft_text),
        PromptMessage(role="user", content=refinement_prompt),
    )


def generate_answer_text(
    *,
    ollama_client,
    model: str,
    messages: tuple[PromptMessage, ...],
    task_mode: str,
    reasoning_mode: str,
    recursive_refinement_enabled: bool,
    recursive_refinement_reasoning_modes: set[str],
) -> str:
    """Optionally refine the first draft through a bounded self-critique loop."""
    draft_text = ollama_client.chat_with_options(
        model=model,
        messages=messages,
        options=answer_generation_options(
            model,
            task_mode=task_mode,
            reasoning_mode=reasoning_mode,
        ),
    )
    final_text = draft_text
    if (
        not recursive_refinement_enabled
        or reasoning_mode not in recursive_refinement_reasoning_modes
    ):
        return _repair_if_needed(
            ollama_client=ollama_client,
            model=model,
            base_messages=messages,
            draft_text=final_text,
            task_mode=task_mode,
            reasoning_mode=reasoning_mode,
        )

    critique_text = ollama_client.chat_with_options(
        model=model,
        messages=build_critique_messages(
            base_messages=messages,
            draft_text=draft_text,
        ),
        options=critique_generation_options(
            model,
            task_mode=task_mode,
        ),
    )
    final_text = ollama_client.chat_with_options(
        model=model,
        messages=build_refinement_messages(
            base_messages=messages,
            draft_text=draft_text,
            critique_text=critique_text,
        ),
        options=refinement_generation_options(
            model,
            task_mode=task_mode,
            reasoning_mode=reasoning_mode,
        ),
    )
    return _repair_if_needed(
        ollama_client=ollama_client,
        model=model,
        base_messages=messages,
        draft_text=final_text,
        task_mode=task_mode,
        reasoning_mode=reasoning_mode,
    )


def _repair_if_needed(
    *,
    ollama_client,
    model: str,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
    task_mode: str,
    reasoning_mode: str,
) -> str:
    current_text = draft_text
    acceptance = assess_answer_quality(
        answer_text=current_text,
        task_mode=task_mode,
        base_messages=base_messages,
    )
    if acceptance.passed:
        return current_text

    for retry_index in range(3):
        current_text = ollama_client.chat_with_options(
            model=model,
            messages=build_repair_messages(
                base_messages=base_messages,
                draft_text=current_text,
                issues=acceptance.issues,
            ),
            options=repair_generation_options(
                model,
                task_mode=task_mode,
                reasoning_mode=reasoning_mode,
                retry_index=retry_index,
            ),
        )
        acceptance = assess_answer_quality(
            answer_text=current_text,
            task_mode=task_mode,
            base_messages=base_messages,
        )
        if acceptance.passed:
            return current_text

    return current_text

"""Refinement helpers for executor-generated artifacts."""

from __future__ import annotations

from application.agent_runtime.executor_prompting import (
    build_executor_approver_prompt,
    build_executor_critique_prompt,
    build_executor_refinement_prompt,
)
from application.agent_runtime.instruction_set import (
    EXECUTOR_APPROVER_SYSTEM_PROMPT,
    EXECUTOR_CRITIQUE_SYSTEM_PROMPT,
    EXECUTOR_REFINEMENT_SYSTEM_PROMPT,
    EXECUTOR_REPAIR_SYSTEM_PROMPT,
    build_executor_repair_prompt,
)
from application.agent_runtime.prompts import sanitize_structured_artifact
from domain.models import PromptMessage

_EXECUTOR_DISCUSSION_ROUNDS = 2
_EXECUTOR_APPROVAL_ROUNDS = 2
_MODULE_DRAFT_HEADINGS = (
    "Target",
    "Intent",
    "Suggested Files",
    "Draft",
    "Integration Notes",
    "Validation Notes",
)
_PATCH_PLAN_HEADINGS = (
    "Scope",
    "Files",
    "Edits",
    "Risks",
    "Validation Order",
)


def refine_executor_artifact(
    *,
    artifact_kind: str,
    draft_text: str,
    action,
    context,
    ollama_client,
    action_generation_options,
) -> str:
    headings = _MODULE_DRAFT_HEADINGS if artifact_kind == "module_draft" else _PATCH_PLAN_HEADINGS

    def _ensure_structured_executor_artifact(candidate_text: str) -> str:
        cleaned = sanitize_structured_artifact(
            candidate_text,
            headings=headings,
        )
        if cleaned.startswith(headings[0]):
            return cleaned
        repaired = ollama_client.chat_with_options(
            model=context.model,
            messages=(
                PromptMessage(role="system", content=EXECUTOR_REPAIR_SYSTEM_PROMPT),
                PromptMessage(
                    role="user",
                    content=build_executor_repair_prompt(
                        artifact_kind=artifact_kind,
                        draft_text=cleaned,
                    ),
                ),
            ),
            options=action_generation_options(context.model),
        )
        repaired = sanitize_structured_artifact(
            repaired,
            headings=headings,
        )
        return repaired if repaired.startswith(headings[0]) else cleaned

    draft_text = _ensure_structured_executor_artifact(draft_text)
    if not context.multi_model_discussion_enabled:
        return draft_text

    discussion_models = [
        (context.critic_model or "").strip(),
        (context.synthesis_model or "").strip(),
    ]
    discussion_models = [item for item in discussion_models if item]
    if not discussion_models:
        return draft_text

    current_draft = draft_text
    for round_index in range(_EXECUTOR_DISCUSSION_ROUNDS):
        discussion_model = discussion_models[min(round_index, len(discussion_models) - 1)]
        try:
            critique_text = ollama_client.chat_with_options(
                model=discussion_model,
                messages=(
                    PromptMessage(role="system", content=EXECUTOR_CRITIQUE_SYSTEM_PROMPT),
                    PromptMessage(
                        role="user",
                        content=build_executor_critique_prompt(
                            artifact_kind=artifact_kind,
                            request_text=context.request_text,
                            instruction=action.instruction,
                            draft_text=current_draft,
                        ),
                    ),
                ),
                options=action_generation_options(discussion_model),
            )
        except RuntimeError:
            return current_draft

        try:
            current_draft = ollama_client.chat_with_options(
                model=context.model,
                messages=(
                    PromptMessage(role="system", content=EXECUTOR_REFINEMENT_SYSTEM_PROMPT),
                    PromptMessage(
                        role="user",
                        content=build_executor_refinement_prompt(
                            artifact_kind=artifact_kind,
                            request_text=context.request_text,
                            instruction=action.instruction,
                            draft_text=current_draft,
                            critique_text=critique_text,
                        ),
                    ),
                ),
                options=action_generation_options(context.model),
            )
            current_draft = _ensure_structured_executor_artifact(current_draft)
        except RuntimeError:
            return current_draft

    approver_model = (context.approver_model or context.model or "").strip()
    if not approver_model:
        return current_draft

    for _ in range(_EXECUTOR_APPROVAL_ROUNDS):
        try:
            approval_text = ollama_client.chat_with_options(
                model=approver_model,
                messages=(
                    PromptMessage(role="system", content=EXECUTOR_APPROVER_SYSTEM_PROMPT),
                    PromptMessage(
                        role="user",
                        content=build_executor_approver_prompt(
                            artifact_kind=artifact_kind,
                            request_text=context.request_text,
                            instruction=action.instruction,
                            draft_text=current_draft,
                        ),
                    ),
                ),
                options=action_generation_options(approver_model),
            )
        except RuntimeError:
            return current_draft

        first_line = approval_text.strip().splitlines()[0] if approval_text.strip() else ""
        if first_line.upper().startswith("APPROVED"):
            return current_draft

        try:
            current_draft = ollama_client.chat_with_options(
                model=context.model,
                messages=(
                    PromptMessage(role="system", content=EXECUTOR_REFINEMENT_SYSTEM_PROMPT),
                    PromptMessage(
                        role="user",
                        content=build_executor_refinement_prompt(
                            artifact_kind=artifact_kind,
                            request_text=context.request_text,
                            instruction=action.instruction,
                            draft_text=current_draft,
                            critique_text=approval_text,
                        ),
                    ),
                ),
                options=action_generation_options(context.model),
            )
            current_draft = _ensure_structured_executor_artifact(current_draft)
        except RuntimeError:
            return current_draft

    return current_draft


__all__ = [
    "refine_executor_artifact",
]

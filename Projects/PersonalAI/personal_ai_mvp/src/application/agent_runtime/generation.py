"""Generation helpers for agent runtime planning artifacts."""

from __future__ import annotations

from typing import Callable

from application.agent_runtime.instruction_set import (
    PLANNING_APPROVER_SYSTEM_PROMPT,
    PLANNING_REPAIR_SYSTEM_PROMPT,
    build_planning_approval_review_prompt,
    build_planning_repair_prompt,
)
from application.agent_runtime.prompts import parse_planning_sections, sanitize_planning_artifact
from domain.models import AgentRuntimeDiscussionTrace
from domain.models import PromptMessage


def generate_planning_output(
    *,
    ollama_client,
    model: str,
    messages: tuple[PromptMessage, ...],
    reasoning_mode: str,
    discussion_preset: str | None,
    recursive_refinement_enabled: bool,
    recursive_refinement_reasoning_modes: set[str],
    multi_model_discussion_enabled: bool,
    critic_model: str | None,
    synthesis_model: str | None,
    approver_model: str | None,
    planning_generation_options: Callable[[str], dict[str, object]],
    critique_generation_options: Callable[[str], dict[str, object]],
    refinement_generation_options: Callable[[str], dict[str, object]],
    build_recursive_critique_messages: Callable[..., tuple[PromptMessage, ...]],
    build_recursive_refinement_messages: Callable[..., tuple[PromptMessage, ...]],
) -> tuple[str, AgentRuntimeDiscussionTrace | None]:
    """Generate the planning artifact, optionally refining it through self-critique."""
    base_planning_prompt = messages[-1].content if messages else ""

    def _ensure_structured_plan(candidate_text: str, *, repair_model: str) -> str:
        cleaned = sanitize_planning_artifact(candidate_text)
        cleaned_sections = parse_planning_sections(cleaned)
        if cleaned.startswith("Goal") and len(cleaned_sections) >= 8:
            return cleaned
        repaired = ollama_client.chat_with_options(
            model=repair_model,
            messages=(
                PromptMessage(role="system", content=PLANNING_REPAIR_SYSTEM_PROMPT),
                PromptMessage(
                    role="user",
                    content=build_planning_repair_prompt(cleaned),
                ),
            ),
            options=refinement_generation_options(repair_model),
        )
        repaired = sanitize_planning_artifact(repaired)
        repaired_sections = parse_planning_sections(repaired)
        if repaired.startswith("Goal") and len(repaired_sections) >= 8:
            return repaired
        from application.agent_runtime.prompts import build_structured_plan_fallback_from_prompt

        return build_structured_plan_fallback_from_prompt(base_planning_prompt)

    def _build_approver_messages(candidate_text: str) -> tuple[PromptMessage, ...]:
        return (
            PromptMessage(
                role="system",
                content=PLANNING_APPROVER_SYSTEM_PROMPT,
            ),
            PromptMessage(
                role="user",
                content=build_planning_approval_review_prompt(candidate_text),
            ),
        )

    def _is_approval_granted(approval_text: str) -> bool:
        first_line = approval_text.strip().splitlines()[0] if approval_text.strip() else ""
        return first_line.upper().startswith("APPROVED")

    def _run_approver_loop(
        candidate_text: str,
        *,
        selected_approver_model: str,
        allow_revisions: bool,
    ) -> tuple[str, str | None, str | None, int, int]:
        nonlocal planner_revisions
        nonlocal planner_rollbacks

        current_text = candidate_text
        approver_text: str | None = None
        current_status: str | None = None
        max_rounds = 2 if allow_revisions else 1
        for _ in range(max_rounds):
            approval_text = ollama_client.chat_with_options(
                model=selected_approver_model,
                messages=_build_approver_messages(current_text),
                options=critique_generation_options(selected_approver_model),
            )
            approver_text = approval_text
            current_status = "approved" if _is_approval_granted(approval_text) else "needs_revision"
            if current_status == "approved" or not allow_revisions:
                break
            planner_rollbacks += 1
            planner_revisions += 1
            current_text = ollama_client.chat_with_options(
                model=model,
                messages=build_recursive_refinement_messages(
                    base_messages=messages,
                    draft_text=current_text,
                    critique_text=approval_text,
                ),
                options=refinement_generation_options(model),
            )
            current_text = _ensure_structured_plan(current_text, repair_model=model)
        return current_text, approver_text, current_status, planner_revisions, planner_rollbacks

    def _run_recursive_self_refinement(draft_text: str) -> tuple[str, AgentRuntimeDiscussionTrace | None]:
        if (
            not recursive_refinement_enabled
            or reasoning_mode not in recursive_refinement_reasoning_modes
        ):
            return draft_text, None

        critique_text = ollama_client.chat_with_options(
            model=model,
            messages=build_recursive_critique_messages(
                base_messages=messages,
                draft_text=draft_text,
            ),
            options=critique_generation_options(model),
        )
        refined = ollama_client.chat_with_options(
            model=model,
            messages=build_recursive_refinement_messages(
                base_messages=messages,
                draft_text=draft_text,
                critique_text=critique_text,
            ),
            options=refinement_generation_options(model),
        )
        refined = _ensure_structured_plan(refined, repair_model=model)
        return refined, None

    planner_revisions = 0
    planner_rollbacks = 0
    approver_feedback: str | None = None
    approval_status: str | None = None

    draft_text = ollama_client.chat_with_options(
        model=model,
        messages=messages,
        options=planning_generation_options(model),
    )
    draft_text = _ensure_structured_plan(draft_text, repair_model=model)
    if multi_model_discussion_enabled:
        selected_critic_model = (critic_model or model).strip()
        selected_synthesis_model = (synthesis_model or model).strip()
        try:
            critique_text = ollama_client.chat_with_options(
                model=selected_critic_model,
                messages=build_recursive_critique_messages(
                    base_messages=messages,
                    draft_text=draft_text,
                ),
                options=critique_generation_options(selected_critic_model),
            )
        except RuntimeError:
            return _run_recursive_self_refinement(draft_text)
        try:
            synthesis_text = ollama_client.chat_with_options(
                model=selected_synthesis_model,
                messages=build_recursive_refinement_messages(
                    base_messages=messages,
                    draft_text=draft_text,
                    critique_text=critique_text,
                ),
                options=refinement_generation_options(selected_synthesis_model),
            )
            synthesis_text = _ensure_structured_plan(
                synthesis_text,
                repair_model=selected_synthesis_model,
            )
            selected_approver_model = (approver_model or selected_synthesis_model or model).strip()
            synthesis_text, approver_feedback, approval_status, _, _ = _run_approver_loop(
                synthesis_text,
                selected_approver_model=selected_approver_model,
                allow_revisions=True,
            )
            return (
                synthesis_text,
                AgentRuntimeDiscussionTrace(
                    preset=discussion_preset or "custom",
                    planner_draft=draft_text,
                    critic_feedback=critique_text,
                    synthesis_output=synthesis_text,
                    approver_feedback=approver_feedback,
                    approval_status=approval_status,
                    planner_revisions=planner_revisions,
                    planner_rollbacks=planner_rollbacks,
                ),
            )
        except RuntimeError:
            final_text, _ = _run_recursive_self_refinement(draft_text)
            selected_approver_model = (approver_model or selected_synthesis_model or model).strip()
            final_text, approver_feedback, approval_status, _, _ = _run_approver_loop(
                final_text,
                selected_approver_model=selected_approver_model,
                allow_revisions=False,
            )
            return (
                final_text,
                AgentRuntimeDiscussionTrace(
                    preset=discussion_preset or "custom",
                    planner_draft=draft_text,
                    critic_feedback=critique_text,
                    synthesis_output=final_text,
                    approver_feedback=approver_feedback,
                    approval_status=approval_status,
                    planner_revisions=planner_revisions,
                    planner_rollbacks=planner_rollbacks,
                    fallback_used="self_refinement_after_synthesis_failure",
                ),
            )
    return _run_recursive_self_refinement(draft_text)

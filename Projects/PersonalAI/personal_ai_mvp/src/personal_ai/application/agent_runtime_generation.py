"""Generation helpers for agent runtime planning artifacts."""

from __future__ import annotations

from typing import Callable

from personal_ai.domain.models import AgentRuntimeDiscussionTrace
from personal_ai.domain.models import PromptMessage


def generate_planning_output(
    *,
    ollama_client,
    model: str,
    messages: tuple[PromptMessage, ...],
    reasoning_mode: str,
    recursive_refinement_enabled: bool,
    recursive_refinement_reasoning_modes: set[str],
    multi_model_discussion_enabled: bool,
    critic_model: str | None,
    synthesis_model: str | None,
    planning_generation_options: Callable[[str], dict[str, object]],
    critique_generation_options: Callable[[str], dict[str, object]],
    refinement_generation_options: Callable[[str], dict[str, object]],
    build_recursive_critique_messages: Callable[..., tuple[PromptMessage, ...]],
    build_recursive_refinement_messages: Callable[..., tuple[PromptMessage, ...]],
) -> tuple[str, AgentRuntimeDiscussionTrace | None]:
    """Generate the planning artifact, optionally refining it through self-critique."""
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
        return refined, None

    draft_text = ollama_client.chat_with_options(
        model=model,
        messages=messages,
        options=planning_generation_options(model),
    )
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
            return (
                synthesis_text,
                AgentRuntimeDiscussionTrace(
                    preset="custom",
                    planner_draft=draft_text,
                    critic_feedback=critique_text,
                    synthesis_output=synthesis_text,
                ),
            )
        except RuntimeError:
            final_text, _ = _run_recursive_self_refinement(draft_text)
            return (
                final_text,
                AgentRuntimeDiscussionTrace(
                    preset="custom",
                    planner_draft=draft_text,
                    critic_feedback=critique_text,
                    synthesis_output=None,
                    fallback_used="self_refinement_after_synthesis_failure",
                ),
            )
    return _run_recursive_self_refinement(draft_text)

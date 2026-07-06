"""Action-prompt assembly helpers for the agent runtime executor stage."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from personal_ai.application.agent_runtime_action_context import (
    build_action_prompt_context_parts,
    repo_summary_text,
)
from personal_ai.application.agent_runtime_prompts import (
    build_module_draft_prompt,
    build_patch_plan_prompt,
    build_planner_handoff,
    build_target_file_context,
    build_validation_baseline,
)
from personal_ai.application.agent_tool_registry import AgentToolContext
from personal_ai.domain.models import AgentRuntimeAction


def build_module_draft_action_prompt(
    *,
    action: AgentRuntimeAction,
    context: AgentToolContext,
    build_file_tree_summary: Callable[[Path], str],
    excerpt_builder: Callable[[str, int], str],
    find_repo_files: Callable[[Path, str, int], list[str]],
    build_validation_plan: Callable[[dict[str, str], str | None], str],
    filter_repo_like_paths,
) -> str:
    """Build the grounded module-draft prompt for one executor action."""
    prompt_context = build_action_prompt_context_parts(
        retrieval_notes=context.retrieval_notes,
        citations=context.citations,
        resolved_repo_path=context.resolved_repo_path,
        build_file_tree_summary=build_file_tree_summary,
        build_config_summary=context.build_config_summary,
        excerpt_builder=excerpt_builder,
        excerpt_limit=140,
        action_target=action.target,
        request_text=context.request_text,
        find_repo_files=find_repo_files,
    )
    target_file_context = build_target_file_context(context)
    validation_baseline = build_validation_baseline(
        context,
        build_validation_plan=build_validation_plan,
    )
    planner_handoff = build_planner_handoff(
        context.planning_output,
        resolved_repo_path=context.resolved_repo_path,
        filter_repo_like_paths=filter_repo_like_paths,
    )
    return build_module_draft_prompt(
        context=context,
        action_title=action.title,
        action_target=action.target,
        action_instruction=action.instruction,
        repo_summary_text=repo_summary_text(context.repo_summary),
        file_tree_summary=prompt_context.file_tree_summary,
        build_config_summary=prompt_context.build_config_summary,
        suggested_files=prompt_context.suggested_files,
        related_files=prompt_context.related_files,
        target_file_context=target_file_context,
        validation_baseline=validation_baseline,
        planner_handoff=planner_handoff,
        notes_block=prompt_context.notes_block,
        citations=prompt_context.citations,
    )


def build_patch_plan_action_prompt(
    *,
    action: AgentRuntimeAction,
    context: AgentToolContext,
    build_file_tree_summary: Callable[[Path], str],
    excerpt_builder: Callable[[str, int], str],
    find_repo_files: Callable[[Path, str, int], list[str]],
    build_validation_plan: Callable[[dict[str, str], str | None], str],
) -> str:
    """Build the grounded patch-plan prompt for one executor action."""
    prompt_context = build_action_prompt_context_parts(
        retrieval_notes=context.retrieval_notes,
        citations=context.citations,
        resolved_repo_path=context.resolved_repo_path,
        build_file_tree_summary=build_file_tree_summary,
        build_config_summary=context.build_config_summary,
        excerpt_builder=excerpt_builder,
        excerpt_limit=120,
        action_target=action.target,
        request_text=context.request_text,
        find_repo_files=find_repo_files,
    )
    validation_baseline = build_validation_baseline(
        context,
        build_validation_plan=build_validation_plan,
    )
    return build_patch_plan_prompt(
        context=context,
        action_title=action.title,
        action_target=action.target,
        action_instruction=action.instruction,
        repo_summary_text=repo_summary_text(context.repo_summary),
        file_tree_summary=prompt_context.file_tree_summary,
        build_config_summary=prompt_context.build_config_summary,
        suggested_files=prompt_context.suggested_files,
        related_files=prompt_context.related_files,
        validation_baseline=validation_baseline,
        notes_block=prompt_context.notes_block,
        citations=prompt_context.citations,
    )

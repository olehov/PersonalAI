"""Helpers for assembling action-execution context in the agent runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from application.agent_runtime.tool_registry import AgentToolContext


def build_action_execution_context(
    *,
    answer_bundle,
    model: str,
    critic_model: str | None,
    synthesis_model: str | None,
    approver_model: str | None,
    discussion_preset: str | None,
    multi_model_discussion_enabled: bool,
    request_text: str,
    normalized_goal: str,
    planning_output: str,
    scope_dirs: tuple[str, ...],
    resolve_repo_path: Callable[[str, str, tuple[str, ...], tuple[str, ...]], Path | None],
    inspect_repo_summary: Callable[[Path], dict[str, str]],
    build_config_summary: Callable[[Path], str],
    collect_target_file_snippets: Callable[[Path | None, str, str], tuple[tuple[str, str], ...]],
) -> AgentToolContext:
    """Assemble the tool execution context from retrieval and repository state."""
    retrieval_notes = {
        item.note.path.as_posix(): item.note
        for item in (
            *answer_bundle.retrieval.primary_notes,
            *answer_bundle.retrieval.related_notes,
        )
    }
    resolved_repo_path = resolve_repo_path(
        normalized_goal,
        request_text,
        scope_dirs,
        answer_bundle.citations,
    )
    repo_summary = (
        inspect_repo_summary(resolved_repo_path)
        if resolved_repo_path is not None
        else None
    )
    config_summary = (
        build_config_summary(resolved_repo_path)
        if resolved_repo_path is not None
        else None
    )
    target_file_snippets = collect_target_file_snippets(
        resolved_repo_path,
        request_text,
        planning_output,
    )
    return AgentToolContext(
        retrieval_notes=retrieval_notes,
        resolved_repo_path=resolved_repo_path,
        repo_summary=repo_summary,
        build_config_summary=config_summary,
        target_file_snippets=target_file_snippets,
        model=model,
        critic_model=critic_model,
        synthesis_model=synthesis_model,
        approver_model=approver_model,
        discussion_preset=discussion_preset,
        multi_model_discussion_enabled=multi_model_discussion_enabled,
        request_text=request_text,
        normalized_goal=normalized_goal,
        planning_output=planning_output,
        citations=answer_bundle.citations,
    )

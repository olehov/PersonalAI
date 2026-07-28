"""Inspection-oriented action executors for the agent runtime."""

from __future__ import annotations

from pathlib import Path

from domain.models import AgentRuntimeActionExecution


def execute_inspect_note(
    action,
    context,
    *,
    compact_excerpt,
) -> AgentRuntimeActionExecution:
    note = context.retrieval_notes.get(action.target)
    if note is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="failed",
            output_text="Grounded note was not available in the retrieved context bundle.",
        )
    excerpt = compact_excerpt(note.content)
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"title={note.title}\n"
            f"path={note.path.as_posix()}\n"
            f"link_count={len(note.links)}\n"
            f"excerpt={excerpt}"
        ),
    )


def execute_inspect_repo(
    action,
    context,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="failed",
            output_text="Could not resolve a grounded repository path from the current request and scope.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status="executed",
        output_text=repo_summary["summary"],
    )


def execute_plan_validation(
    action,
    context,
    *,
    build_validation_plan,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Validation planning needs a resolved project directory before concrete commands can be proposed.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status="executed",
        output_text=build_validation_plan(
            repo_summary,
            context.build_config_summary,
        ),
    )


def execute_inspect_file_tree(
    action,
    context,
    *,
    vault_root: Path,
    build_file_tree_summary,
) -> AgentRuntimeActionExecution:
    resolved_repo_path = context.resolved_repo_path
    if resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="File-tree inspection needs a resolved repository path before it can enumerate project files.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=resolved_repo_path.relative_to(vault_root).as_posix(),
        status="executed",
        output_text=build_file_tree_summary(resolved_repo_path),
    )


def execute_inspect_build_config(
    action,
    context,
    *,
    vault_root: Path,
    build_config_summary,
) -> AgentRuntimeActionExecution:
    resolved_repo_path = context.resolved_repo_path
    if resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Build-config inspection needs a resolved repository path before it can inspect manifests.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=resolved_repo_path.relative_to(vault_root).as_posix(),
        status="executed",
        output_text=context.build_config_summary
        or build_config_summary(resolved_repo_path),
    )


def execute_inspect_target_files(
    action,
    context,
) -> AgentRuntimeActionExecution:
    if not context.target_file_snippets:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                "Target-file inspection needs a resolved repository path and at least one concrete file hint from the planner or repo scan."
            ),
        )
    preview_lines: list[str] = []
    for path, snippet in context.target_file_snippets.items():
        preview_lines.append(f"path={path}")
        preview_lines.append(snippet)
        preview_lines.append("")
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text="\n".join(preview_lines).strip(),
    )


__all__ = [
    "execute_inspect_build_config",
    "execute_inspect_file_tree",
    "execute_inspect_note",
    "execute_inspect_repo",
    "execute_inspect_target_files",
    "execute_plan_validation",
]

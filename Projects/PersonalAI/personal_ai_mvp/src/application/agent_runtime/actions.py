"""Safe execution adapters for agent runtime actions."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from application.agent_runtime.action_inspectors import (
    execute_inspect_build_config,
    execute_inspect_file_tree,
    execute_inspect_note,
    execute_inspect_repo,
    execute_inspect_target_files,
    execute_plan_validation,
)
from application.agent_runtime.action_refinement import (
    refine_executor_artifact,
)
from application.agent_runtime.action_scaffold_support import (
    build_scaffold_context_for_file,
    dedupe_scaffold_tree_manifest,
    looks_like_bad_scaffold_output,
    parse_scaffold_tree_manifest,
)
from application.agent_runtime.action_support import (
    build_probe_file_content,
    manifest_has_only_runtime_scaffold_paths,
    persist_artifact_draft,
    resolve_allowed_command,
    resolve_safe_repo_write_path,
    runtime_scaffold_dir_name,
    scaffold_path,
)
from application.agent_runtime.instruction_set import (
    MODULE_DRAFT_SYSTEM_PROMPT,
    PATCH_PLAN_SYSTEM_PROMPT,
    SCAFFOLD_FILE_SYSTEM_PROMPT,
    SCAFFOLD_TREE_SYSTEM_PROMPT,
)
from application.agent_runtime.executor_prompting import (
    build_scaffold_file_prompt,
    build_scaffold_tree_prompt,
    strip_markdown_fences,
)
from application.agent_runtime.prompts import sanitize_structured_artifact
from application.agent_runtime.scaffold_templates import (
    fallback_scaffold_file_content,
    fallback_scaffold_tree_manifest,
)
from application.agent_runtime.tool_registry import AgentToolContext
from domain.models import AgentRuntimeAction, AgentRuntimeActionExecution, PromptMessage

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


def execute_draft_module(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    vault_root: Path,
    build_module_draft_prompt,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Module drafting needs a resolved repository path and repo summary before a grounded draft can be produced.",
        )

    prompt = build_module_draft_prompt(action, context)
    draft_text = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=MODULE_DRAFT_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    )
    draft_text = sanitize_structured_artifact(
        draft_text,
        headings=_MODULE_DRAFT_HEADINGS,
    )
    draft_text = refine_executor_artifact(
        artifact_kind="module_draft",
        draft_text=draft_text,
        action=action,
        context=context,
        ollama_client=ollama_client,
        action_generation_options=action_generation_options,
    )
    saved_path = persist_artifact_draft(
        vault_root=vault_root,
        resolved_repo_path=context.resolved_repo_path,
        kind="module_draft",
        target=action.target,
        content=draft_text,
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"saved_path={saved_path}\n\n{draft_text}"
            if saved_path is not None
            else draft_text
        ),
    )


def execute_plan_patch(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    vault_root: Path,
    build_patch_plan_prompt,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Patch planning needs a resolved repository path and repo summary before a grounded patch plan can be produced.",
        )
    prompt = build_patch_plan_prompt(action, context)
    patch_plan_text = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=PATCH_PLAN_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    )
    patch_plan_text = sanitize_structured_artifact(
        patch_plan_text,
        headings=_PATCH_PLAN_HEADINGS,
    )
    patch_plan_text = refine_executor_artifact(
        artifact_kind="patch_plan",
        draft_text=patch_plan_text,
        action=action,
        context=context,
        ollama_client=ollama_client,
        action_generation_options=action_generation_options,
    )
    saved_path = persist_artifact_draft(
        vault_root=vault_root,
        resolved_repo_path=context.resolved_repo_path,
        kind="patch_plan",
        target=action.target,
        content=patch_plan_text,
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"saved_path={saved_path}\n\n{patch_plan_text}"
            if saved_path is not None
            else patch_plan_text
        ),
    )


def execute_run_allowed_command(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    recommend_validation_commands,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    resolved_repo_path = context.resolved_repo_path
    if repo_summary is None or resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Command execution needs a resolved repository path and validation baseline.",
        )
    recommended = recommend_validation_commands(
        repo_summary=repo_summary,
        build_config_summary=context.build_config_summary,
    )
    if not recommended:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=repo_summary["display_path"],
            status="deferred",
            output_text="No safe validation command was inferred from the current repository markers.",
        )
    attempts: list[str] = []
    final_status = "failed"
    output_lines: list[str] = []
    for index, selected in enumerate(recommended, start=1):
        argv = resolve_allowed_command(selected)
        if argv is None:
            attempts.append(
                "\n".join(
                    [
                        f"attempt={index}",
                        f"command={selected}",
                        "status=deferred",
                        "reason=Validation command is not in the safe whitelist or the executable is unavailable.",
                    ]
                )
            )
            continue
        try:
            completed = subprocess.run(
                argv,
                cwd=resolved_repo_path,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            attempts.append(
                "\n".join(
                    [
                        f"attempt={index}",
                        f"command={selected}",
                        "status=failed",
                        f"error={exc}",
                    ]
                )
            )
            continue

        stdout_preview = (completed.stdout or "").strip()
        stderr_preview = (completed.stderr or "").strip()
        attempt_lines = [
            f"attempt={index}",
            f"command={selected}",
            f"cwd={repo_summary['display_path']}",
            f"exit_code={completed.returncode}",
        ]
        if stdout_preview:
            attempt_lines.append(f"stdout={stdout_preview[:1600]}")
        if stderr_preview:
            attempt_lines.append(f"stderr={stderr_preview[:1600]}")
        attempts.append("\n".join(attempt_lines))
        if completed.returncode == 0:
            final_status = "executed"
            output_lines = attempt_lines
            break

    if not output_lines:
        output_lines = ["All recommended validation commands failed or were unavailable.", *attempts]
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status=final_status,
        output_text="\n".join(output_lines),
    )


def execute_create_dir(
    action: AgentRuntimeAction,
    context: AgentToolContext,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    target_path, error = resolve_safe_repo_write_path(
        resolved_repo_path=context.resolved_repo_path,
        target=action.target,
    )
    if repo_summary is None or target_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=error or "Could not resolve a safe repository directory target.",
        )
    if target_path.exists():
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                f"Directory already exists and was left unchanged: "
                f"{target_path.relative_to(context.resolved_repo_path).as_posix()}"
            ),
        )
    target_path.mkdir(parents=True, exist_ok=False)
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"created_dir={target_path.relative_to(context.resolved_repo_path).as_posix()}\n"
            f"repo={repo_summary['display_path']}"
        ),
    )


def execute_create_file(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    action_generation_options,
    scaffold_context: str | None = None,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    target_path, error = resolve_safe_repo_write_path(
        resolved_repo_path=context.resolved_repo_path,
        target=action.target,
    )
    if repo_summary is None or target_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=error or "Could not resolve a safe repository file target.",
        )
    if target_path.exists():
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                f"File already exists and was left unchanged: "
                f"{target_path.relative_to(context.resolved_repo_path).as_posix()}"
            ),
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lowered_instruction = action.instruction.casefold()
    if "probe" in lowered_instruction:
        file_content = build_probe_file_content(
            repo_display_path=repo_summary["display_path"],
            target=action.target,
            request_text=context.request_text,
            instruction=action.instruction,
        )
    else:
        prompt = build_scaffold_file_prompt(
            repo_display_path=repo_summary["display_path"],
            target=action.target,
            request_text=context.request_text,
            instruction=action.instruction,
            build_config_summary=context.build_config_summary,
            target_file_snippets=context.target_file_snippets,
            scaffold_context=scaffold_context,
        )
        generated = ollama_client.chat_with_options(
            model=context.model,
            messages=(
                PromptMessage(role="system", content=SCAFFOLD_FILE_SYSTEM_PROMPT),
                PromptMessage(role="user", content=prompt),
            ),
            options=action_generation_options(context.model),
        ).strip()
        generated = strip_markdown_fences(generated)
        if looks_like_bad_scaffold_output(
            content=generated,
            target=action.target,
            request_text=context.request_text,
            expected_scaffold_paths=None,
        ):
            file_content = fallback_scaffold_file_content(action.target)
        else:
            file_content = generated
    target_path.write_text(
        file_content,
        encoding="utf-8",
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"created_file={target_path.relative_to(context.resolved_repo_path).as_posix()}\n"
            f"repo={repo_summary['display_path']}"
        ),
    )


def execute_create_scaffold_tree(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None or context.resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Scaffold-tree creation needs a resolved repository path before safe writes can be applied.",
        )

    prompt = build_scaffold_tree_prompt(
        repo_display_path=repo_summary["display_path"],
        request_text=context.request_text,
        instruction=action.instruction,
        build_config_summary=context.build_config_summary,
        target_file_snippets=context.target_file_snippets,
        scaffold_root_dir_name=runtime_scaffold_dir_name(),
    )
    generated = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=SCAFFOLD_TREE_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    ).strip()
    parsed = parse_scaffold_tree_manifest(generated)
    if parsed is None:
        dirs, files = fallback_scaffold_tree_manifest(
            context.request_text,
            scaffold_root=runtime_scaffold_dir_name(),
        )
    else:
        dirs, files = parsed
    if not manifest_has_only_runtime_scaffold_paths(dirs, files):
        dirs, files = fallback_scaffold_tree_manifest(
            context.request_text,
            scaffold_root=runtime_scaffold_dir_name(),
        )
    dirs, files = dedupe_scaffold_tree_manifest(dirs, files)

    created_dirs: list[str] = []
    created_files: list[str] = []
    skipped: list[str] = []

    for directory in dirs:
        execution = execute_create_dir(
            AgentRuntimeAction(
                action_type="create_dir",
                title=f"Create {directory}",
                target=directory,
                instruction=action.instruction,
                rationale=action.rationale,
            ),
            context,
        )
        if execution.status == "executed":
            created_dirs.append(directory)
        else:
            skipped.append(f"dir:{directory}:{execution.status}")

    for item in files:
        file_path = item["path"]
        file_instruction = (
            f"{action.instruction}\n\nRequested scaffold file purpose: {item['purpose']}"
            if item["purpose"]
            else action.instruction
        )
        execution = execute_create_file(
            AgentRuntimeAction(
                action_type="create_file",
                title=f"Create {file_path}",
                target=file_path,
                instruction=file_instruction,
                rationale=action.rationale,
            ),
            context,
            ollama_client=ollama_client,
            action_generation_options=action_generation_options,
            scaffold_context=build_scaffold_context_for_file(
                file_item=item,
                all_files=files,
            ),
        )
        if execution.status == "executed":
            created_files.append(file_path)
        else:
            skipped.append(f"file:{file_path}:{execution.status}")

    expected_scaffold_paths = {path for path in created_files}
    for file_path in created_files:
        resolved_path, error = resolve_safe_repo_write_path(
            resolved_repo_path=context.resolved_repo_path,
            target=file_path,
        )
        if resolved_path is None or error is not None or not resolved_path.is_file():
            continue
        content = resolved_path.read_text(encoding="utf-8")
        if looks_like_bad_scaffold_output(
            content=content,
            target=file_path,
            request_text=context.request_text,
            expected_scaffold_paths=expected_scaffold_paths,
        ):
            resolved_path.write_text(
                fallback_scaffold_file_content(file_path),
                encoding="utf-8",
            )
            skipped.append(f"repaired:{file_path}:fallback")

    if created_dirs or created_files:
        status = "executed"
    elif skipped:
        status = "deferred"
    else:
        status = "failed"

    lines = [
        f"repo={repo_summary['display_path']}",
        f"created_dir_count={len(created_dirs)}",
        f"created_file_count={len(created_files)}",
    ]
    if created_dirs:
        lines.append(f"created_dirs={'; '.join(created_dirs)}")
    if created_files:
        lines.append(f"created_files={'; '.join(created_files)}")
    if skipped:
        lines.append(f"skipped={'; '.join(skipped)}")
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status=status,
        output_text="\n".join(lines),
    )

"""Tool-registry wiring for the agent runtime."""

from __future__ import annotations

from functools import partial
from typing import Callable

from personal_ai.application.agent_tool_registry import AgentToolRegistry
from personal_ai.application.agent_runtime_actions import (
    execute_create_dir,
    execute_create_file,
    execute_create_scaffold_tree,
    execute_draft_module,
    execute_inspect_build_config,
    execute_inspect_file_tree,
    execute_inspect_note,
    execute_inspect_repo,
    execute_inspect_target_files,
    execute_plan_patch,
    execute_plan_validation,
    execute_run_allowed_command,
)
from personal_ai.infrastructure.ollama_client import OllamaClient


def build_agent_tool_registry(
    *,
    vault_root,
    ollama_client: OllamaClient,
    compact_excerpt: Callable[[str, int], str],
    build_file_tree_summary: Callable,
    build_config_summary: Callable,
    build_module_draft_prompt: Callable,
    build_patch_plan_prompt: Callable,
    action_generation_options: Callable[[str], dict[str, object]],
    build_validation_plan: Callable,
    recommend_validation_commands: Callable,
) -> AgentToolRegistry:
    """Build the runtime tool registry with the current service dependencies bound in."""
    registry = AgentToolRegistry()
    registry.register(
        "inspect_note",
        partial(execute_inspect_note, compact_excerpt=compact_excerpt),
    )
    registry.register("inspect_repo", execute_inspect_repo)
    registry.register(
        "inspect_file_tree",
        partial(
            execute_inspect_file_tree,
            vault_root=vault_root,
            build_file_tree_summary=build_file_tree_summary,
        ),
    )
    registry.register(
        "inspect_build_config",
        partial(
            execute_inspect_build_config,
            vault_root=vault_root,
            build_config_summary=build_config_summary,
        ),
    )
    registry.register("inspect_target_files", execute_inspect_target_files)
    registry.register("create_dir", execute_create_dir)
    registry.register(
        "create_file",
        partial(
            execute_create_file,
            ollama_client=ollama_client,
            action_generation_options=action_generation_options,
        ),
    )
    registry.register(
        "create_scaffold_tree",
        partial(
            execute_create_scaffold_tree,
            ollama_client=ollama_client,
            action_generation_options=action_generation_options,
        ),
    )
    registry.register(
        "draft_module",
        partial(
            execute_draft_module,
            ollama_client=ollama_client,
            vault_root=vault_root,
            build_module_draft_prompt=build_module_draft_prompt,
            action_generation_options=action_generation_options,
        ),
    )
    registry.register(
        "plan_patch",
        partial(
            execute_plan_patch,
            ollama_client=ollama_client,
            vault_root=vault_root,
            build_patch_plan_prompt=build_patch_plan_prompt,
            action_generation_options=action_generation_options,
        ),
    )
    registry.register(
        "plan_validation",
        partial(
            execute_plan_validation,
            build_validation_plan=build_validation_plan,
        ),
    )
    registry.register(
        "run_allowed_command",
        partial(
            execute_run_allowed_command,
            recommend_validation_commands=recommend_validation_commands,
        ),
    )
    return registry

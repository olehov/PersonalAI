"""Repo/context support helpers for AgentRuntimeService."""

from __future__ import annotations

from pathlib import Path

from application.agent_runtime.action_context import (
    render_file_list,
    suggest_first_slice_file_paths,
)
from application.agent_runtime.action_prompts import (
    build_module_draft_action_prompt,
    build_patch_plan_action_prompt,
)
from application.agent_runtime.path_hints import (
    extract_repo_like_paths,
    filter_repo_like_paths,
)
from application.agent_runtime.prompts import (
    build_planning_prompt,
    compact_excerpt,
    render_target_file_context,
)
from application.agent_runtime.repo import (
    build_config_summary,
    build_file_tree_summary,
    build_validation_plan,
    canonicalize_repo_path_hint,
    collect_target_file_snippets,
    find_repo_files,
    inspect_repo_summary,
    read_file_snippet,
    recommend_validation_commands,
)
from application.agent_runtime.locator import resolve_repo_path


class AgentRuntimeRepoSupport:
    """Owns repo discovery, context collection, and prompt scaffolding helpers."""

    def __init__(self, *, vault_root: Path) -> None:
        self._vault_root = vault_root

    def compact_excerpt(self, content: str, *, limit: int = 220) -> str:
        return compact_excerpt(content, limit=limit)

    def resolve_repo_path(
        self,
        *,
        normalized_goal: str,
        request_text: str,
        scope_dirs: tuple[str, ...],
        citations: tuple[str, ...],
    ) -> Path | None:
        return resolve_repo_path(
            vault_root=self._vault_root,
            normalized_goal=normalized_goal,
            request_text=request_text,
            scope_dirs=scope_dirs,
            citations=citations,
        )

    def inspect_repo_summary(self, repo_path: Path) -> dict[str, str]:
        return inspect_repo_summary(repo_path, vault_root=self._vault_root)

    def build_file_tree_summary(self, repo_path: Path) -> str:
        return build_file_tree_summary(repo_path, vault_root=self._vault_root)

    def build_config_summary(self, repo_path: Path) -> str:
        return build_config_summary(repo_path, vault_root=self._vault_root)

    def build_validation_plan(
        self,
        repo_summary: dict[str, str],
        build_config_summary_text: str | None,
    ) -> str:
        return build_validation_plan(repo_summary, build_config_summary_text)

    def recommend_validation_commands(
        self,
        *,
        repo_summary: dict[str, str],
        build_config_summary: str | None,
    ) -> list[str]:
        return recommend_validation_commands(
            repo_summary=repo_summary,
            build_config_summary=build_config_summary,
        )

    def extract_repo_like_paths(self, text: str) -> tuple[str, ...]:
        return extract_repo_like_paths(text)

    def canonicalize_repo_path_hint(
        self,
        path_hint: str,
        *,
        resolved_repo_path: Path | None,
        files_only: bool,
    ) -> str | None:
        return canonicalize_repo_path_hint(
            path_hint,
            vault_root=self._vault_root,
            resolved_repo_path=resolved_repo_path,
            files_only=files_only,
        )

    def filter_repo_like_paths(
        self,
        text: str,
        *,
        resolved_repo_path: Path | None,
        files_only: bool,
    ) -> tuple[str, ...]:
        return filter_repo_like_paths(
            text,
            resolved_repo_path=resolved_repo_path,
            files_only=files_only,
            canonicalize_repo_path_hint=lambda hint, repo_path, files_only_value: self.canonicalize_repo_path_hint(
                hint,
                resolved_repo_path=repo_path,
                files_only=files_only_value,
            ),
        )

    def find_repo_files(
        self,
        repo_path: Path,
        *,
        contains: str,
        limit: int,
    ) -> list[str]:
        return find_repo_files(
            repo_path,
            vault_root=self._vault_root,
            contains=contains,
            limit=limit,
        )

    def collect_target_file_snippets(
        self,
        *,
        resolved_repo_path: Path | None,
        request_text: str,
        planning_output: str,
    ) -> dict[str, str]:
        return collect_target_file_snippets(
            resolved_repo_path=resolved_repo_path,
            request_text=request_text,
            planning_output=planning_output,
            vault_root=self._vault_root,
            extract_repo_like_paths=self.extract_repo_like_paths,
        )

    def build_planning_prompt(
        self,
        *,
        request_text: str,
        normalized_goal: str,
        answer_bundle,
        retrieval_observation: str,
        reasoning_mode: str,
        resolved_repo_path: Path | None,
    ) -> str:
        repo_summary_text = "none"
        file_tree_summary = "none"
        build_config_summary_text = "none"
        suggested_files = "- none"
        target_file_context = "- none"
        if resolved_repo_path is not None:
            repo_summary = self.inspect_repo_summary(resolved_repo_path)
            repo_summary_text = repo_summary["summary"]
            file_tree_summary = self.build_file_tree_summary(resolved_repo_path)
            build_config_summary_text = self.build_config_summary(resolved_repo_path)
            target_file_snippets = self.collect_target_file_snippets(
                resolved_repo_path=resolved_repo_path,
                request_text=request_text,
                planning_output="",
            )
            if target_file_snippets:
                suggested_files = render_file_list(tuple(target_file_snippets.keys()))
                target_file_context = render_target_file_context(target_file_snippets)
        return build_planning_prompt(
            request_text=request_text,
            normalized_goal=normalized_goal,
            answer_prompt=answer_bundle.messages[1].content,
            retrieval_observation=retrieval_observation,
            reasoning_mode=reasoning_mode,
            repo_summary_text=repo_summary_text,
            file_tree_summary=file_tree_summary,
            build_config_summary=build_config_summary_text,
            suggested_files=suggested_files,
            target_file_context=target_file_context,
        )

    def build_module_draft_prompt(self, action, context) -> str:
        return build_module_draft_action_prompt(
            action=action,
            context=context,
            build_file_tree_summary=self.build_file_tree_summary,
            excerpt_builder=lambda content, limit: self.compact_excerpt(
                content,
                limit=limit,
            ),
            find_repo_files=self.find_repo_files_for_context,
            build_validation_plan=self.build_validation_plan,
            filter_repo_like_paths=self.filter_repo_like_paths,
        )

    def build_patch_plan_prompt(self, action, context) -> str:
        return build_patch_plan_action_prompt(
            action=action,
            context=context,
            build_file_tree_summary=self.build_file_tree_summary,
            excerpt_builder=lambda content, limit: self.compact_excerpt(
                content,
                limit=limit,
            ),
            find_repo_files=self.find_repo_files_for_context,
            build_validation_plan=self.build_validation_plan,
            filter_repo_like_paths=self.filter_repo_like_paths,
        )

    def suggest_first_slice_files(self, action, context) -> str:
        return render_file_list(self.suggest_first_slice_file_paths(action, context))

    def suggest_first_slice_file_paths(self, action, context) -> tuple[str, ...]:
        return suggest_first_slice_file_paths(
            action_target=action.target,
            request_text=context.request_text,
            planning_output=context.planning_output,
            resolved_repo_path=context.resolved_repo_path,
            find_repo_files=self.find_repo_files_for_context,
            target_file_snippets=context.target_file_snippets,
        )

    def find_repo_files_for_context(
        self,
        repo_path: Path,
        contains: str,
        limit: int,
    ) -> list[str]:
        return self.find_repo_files(
            repo_path,
            contains=contains,
            limit=limit,
        )

    def read_file_snippet(self, file_path: Path, *, max_lines: int = 40, max_chars: int = 1600) -> str:
        return read_file_snippet(
            file_path,
            max_lines=max_lines,
            max_chars=max_chars,
        )

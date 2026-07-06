"""Planning-oriented agent runtime for project-scale coding requests."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from time import perf_counter

from personal_ai.application.agent_tool_registry import (
    AgentToolContext,
    AgentToolRegistry,
)
from personal_ai.application.agent_runtime_prompts import (
    build_planning_prompt,
    build_retrieval_observation,
    build_system_prompt,
    compact_excerpt,
    extract_plan_lines,
    parse_planning_sections,
    render_target_file_context,
    summarize_retrieval,
)
from personal_ai.application.agent_runtime_action_context import (
    render_file_list,
    suggest_first_slice_file_paths,
)
from personal_ai.application.agent_runtime_action_prompts import (
    build_module_draft_action_prompt,
    build_patch_plan_action_prompt,
)
from personal_ai.application.agent_runtime_artifacts import build_runtime_artifact
from personal_ai.application.agent_runtime_execution_context import (
    build_action_execution_context,
)
from personal_ai.application.agent_runtime_generation import (
    generate_planning_output,
)
from personal_ai.application.agent_runtime_locator import resolve_repo_path
from personal_ai.application.agent_runtime_planning import (
    build_recommended_actions,
    build_recursive_critique_messages,
    build_recursive_refinement_messages,
    build_task_plan,
    compact_history_content,
    merge_conversation_history,
    normalize_conversation_history,
    normalize_goal,
    render_action_executions,
    render_action_plan,
)
from personal_ai.application.agent_runtime_tool_registry_builder import (
    build_agent_tool_registry,
)
from personal_ai.application.agent_runtime_model_options import (
    action_generation_options,
    critique_generation_options,
    is_high_risk_planning_model,
    planning_generation_options,
    refinement_generation_options,
)
from personal_ai.application.agent_runtime_path_hints import (
    extract_repo_like_paths,
    filter_repo_like_paths,
)
from personal_ai.application.agent_runtime_repo import (
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
from personal_ai.application.answer_service import AnswerService
from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    AgentRuntimeArtifact,
    AgentRuntimeStep,
    PromptMessage,
)
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.env_loader import load_env_file, read_bool_env


class AgentRuntimeService:
    """Runs a minimal agent-style loop for large coding requests."""

    _MAX_HISTORY_TURNS = 8
    _MAX_HISTORY_CHARS_PER_MESSAGE = 1_200
    _RECURSIVE_REFINEMENT_REASONING_MODES = {"high"}
    _HIGH_RISK_PLANNING_MODELS = ("deepseek-r1",)
    _DISCUSSION_PRESET_MODELS = {
        "fast": ("gemma3:4b", "gemma:latest", "gemma:latest"),
        "coder_critic": ("qwen2.5-coder:7b", "gemma:latest", "deepseek-r1:8b"),
        "heavy_synthesis": ("gemma:latest", "qwen2.5-coder:7b", "deepseek-r1:8b"),
    }

    SYSTEM_PROMPT = (
        "You are PersonalAI Agent Runtime, a local-first software engineering planning agent. "
        "Your job is to transform large coding requests into grounded, implementation-ready slices. "
        "Do not claim to have edited files, run tests, or completed execution steps unless the runtime explicitly reports that it happened. "
        "Prefer concrete modules, functions, data flow, validation steps, and first-slice outputs over general advice. "
        "Reason carefully before producing a plan: identify the real bottleneck, compare plausible first slices, and choose the safest high-leverage path instead of listing generic work. "
        "Be honest about missing execution capability: when a request needs real filesystem or test execution, produce the safest next slice instead of pretending the work is done."
    )

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        answer_service: AnswerService,
        ollama_client: OllamaClient,
        history_repository=None,
        recursive_refinement_enabled: bool | None = None,
    ) -> None:
        self._knowledge_service = knowledge_service
        self._answer_service = answer_service
        self._ollama_client = ollama_client
        self._history_repository = history_repository
        self._recursive_refinement_enabled = (
            self._default_recursive_refinement_enabled()
            if recursive_refinement_enabled is None
            else recursive_refinement_enabled
        )
        self._multi_model_discussion_enabled = self._default_multi_model_discussion_enabled()
        self._tool_registry = self._build_tool_registry()

    def run(
        self,
        request_text: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        discussion_preset: str | None = None,
    ) -> AgentRuntimeArtifact:
        """Produce a reviewable runtime artifact for a project-scale task."""
        started_at = perf_counter()
        (
            planner_model,
            executor_model,
            critic_model,
            synthesis_model,
            resolved_discussion_preset,
        ) = self._resolve_role_models(
            model,
            discussion_preset=discussion_preset,
        )
        normalized_goal = self._normalize_goal(request_text)
        answer_bundle = self._answer_service.prepare_answer(
            normalized_goal,
            scope_dirs=scope_dirs,
            reasoning_mode=reasoning_mode,
        )
        resolved_repo_path = self._resolve_repo_path(
            normalized_goal=normalized_goal,
            request_text=request_text,
            scope_dirs=scope_dirs,
            citations=answer_bundle.citations,
        )
        retrieval_observation = self._build_retrieval_observation(answer_bundle)
        planning_prompt = self._build_planning_prompt(
            request_text=request_text,
            normalized_goal=normalized_goal,
            answer_bundle=answer_bundle,
            retrieval_observation=retrieval_observation,
            reasoning_mode=reasoning_mode,
            resolved_repo_path=resolved_repo_path,
        )
        planning_messages = self._merge_conversation_history(
            (
                PromptMessage(role="system", content=self._build_system_prompt(reasoning_mode)),
                PromptMessage(role="user", content=planning_prompt),
            ),
            conversation_history,
        )
        planning_output, discussion_trace = self._generate_planning_output(
            model=planner_model,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            messages=planning_messages,
            reasoning_mode=reasoning_mode,
        )
        recommended_actions = self._build_recommended_actions(
            normalized_goal=normalized_goal,
            request_text=request_text,
            answer_bundle=answer_bundle,
        )
        action_executions = self._execute_recommended_actions(
            recommended_actions=recommended_actions,
            answer_bundle=answer_bundle,
            model=executor_model,
            normalized_goal=normalized_goal,
            planning_output=planning_output,
            request_text=request_text,
            scope_dirs=scope_dirs,
        )
        task_plan = self._build_task_plan(
            normalized_goal=normalized_goal,
            planning_output=planning_output,
            recommended_actions=recommended_actions,
        )
        action_plan_text = self._render_action_plan(recommended_actions)
        action_execution_text = self._render_action_executions(action_executions)
        artifact = build_runtime_artifact(
            planner_model=planner_model,
            executor_model=executor_model,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            discussion_preset=resolved_discussion_preset,
            discussion_trace=discussion_trace,
            request_text=request_text,
            normalized_goal=normalized_goal,
            task_mode=answer_bundle.task_mode,
            scope_dirs=scope_dirs,
            citations=answer_bundle.citations,
            retrieval_summary=self._summarize_retrieval(answer_bundle),
            retrieval_observation=retrieval_observation,
            planning_prompt=planning_prompt,
            planning_output=planning_output,
            recommended_actions=recommended_actions,
            action_plan_text=action_plan_text,
            action_executions=action_executions,
            action_execution_text=action_execution_text,
            task_plan=task_plan,
            prompt=answer_bundle,
        )
        if self._history_repository is not None:
            latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
            history_entry = self._history_repository.save_agent_runtime_artifact(
                artifact,
                latency_ms=latency_ms,
            )
            if history_entry is not None and getattr(history_entry, "entry_id", None) is not None:
                artifact = replace(artifact, history_entry_id=history_entry.entry_id)
        return artifact

    def _resolve_role_models(
        self,
        requested_model: str,
        *,
        discussion_preset: str | None,
    ) -> tuple[str, str, str | None, str | None, str | None]:
        """Resolve planner/executor/discussion models from env overrides with safe fallbacks."""
        load_env_file()
        normalized_preset = (discussion_preset or "").strip().lower() or None
        if normalized_preset in self._DISCUSSION_PRESET_MODELS:
            preset_planner, preset_critic, preset_synthesis = self._DISCUSSION_PRESET_MODELS[normalized_preset]
            planner_model = preset_planner
            critic_model = preset_critic
            synthesis_model = preset_synthesis
        else:
            planner_model = os.getenv("PERSONAL_AI_AGENT_PLANNER_MODEL", "").strip() or requested_model.strip()
            critic_model = os.getenv("PERSONAL_AI_AGENT_CRITIC_MODEL", "").strip() or None
            synthesis_model = os.getenv("PERSONAL_AI_AGENT_SYNTHESIS_MODEL", "").strip() or None
        executor_model = os.getenv("PERSONAL_AI_AGENT_EXECUTOR_MODEL", "").strip() or planner_model
        return planner_model, executor_model, critic_model, synthesis_model, normalized_preset

    def _build_task_plan(
        self,
        *,
        normalized_goal: str,
        planning_output: str,
        recommended_actions: tuple[AgentRuntimeAction, ...],
    ):
        return build_task_plan(
            normalized_goal=normalized_goal,
            planning_output=planning_output,
            recommended_actions=recommended_actions,
            parse_planning_sections=self._parse_planning_sections,
            extract_plan_lines=self._extract_plan_lines,
        )

    def _parse_planning_sections(self, planning_output: str) -> dict[str, str]:
        return parse_planning_sections(planning_output)

    def _extract_plan_lines(self, section_text: str) -> list[str]:
        return extract_plan_lines(section_text)

    def _generate_planning_output(
        self,
        *,
        model: str,
        critic_model: str | None,
        synthesis_model: str | None,
        messages: tuple[PromptMessage, ...],
        reasoning_mode: str,
    ):
        return generate_planning_output(
            ollama_client=self._ollama_client,
            model=model,
            messages=messages,
            reasoning_mode=reasoning_mode,
            recursive_refinement_enabled=self._recursive_refinement_enabled,
            recursive_refinement_reasoning_modes=self._RECURSIVE_REFINEMENT_REASONING_MODES,
            multi_model_discussion_enabled=self._multi_model_discussion_enabled,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            planning_generation_options=self._planning_generation_options,
            critique_generation_options=self._critique_generation_options,
            refinement_generation_options=self._refinement_generation_options,
            build_recursive_critique_messages=self._build_recursive_critique_messages,
            build_recursive_refinement_messages=self._build_recursive_refinement_messages,
        )

    def _build_recursive_critique_messages(
        self,
        *,
        base_messages: tuple[PromptMessage, ...],
        draft_text: str,
    ) -> tuple[PromptMessage, ...]:
        return build_recursive_critique_messages(
            base_messages=base_messages,
            draft_text=draft_text,
        )

    def _build_recursive_refinement_messages(
        self,
        *,
        base_messages: tuple[PromptMessage, ...],
        draft_text: str,
        critique_text: str,
    ) -> tuple[PromptMessage, ...]:
        return build_recursive_refinement_messages(
            base_messages=base_messages,
            draft_text=draft_text,
            critique_text=critique_text,
        )

    @classmethod
    def _default_recursive_refinement_enabled(cls) -> bool:
        """Resolve whether recursive planning refinement is enabled from the environment."""
        load_env_file()
        fallback = read_bool_env("PERSONAL_AI_RECURSIVE_REFINEMENT", default=False)
        return read_bool_env(
            "PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT",
            default=fallback,
        )

    @classmethod
    def _default_multi_model_discussion_enabled(cls) -> bool:
        """Resolve whether planner/critic/synthesizer discussion is enabled."""
        load_env_file()
        return read_bool_env(
            "PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION",
            default=True,
        )

    def _build_system_prompt(self, reasoning_mode: str) -> str:
        return build_system_prompt(self.SYSTEM_PROMPT, reasoning_mode)

    def _merge_conversation_history(
        self,
        base_messages: tuple[PromptMessage, ...],
        conversation_history: tuple[PromptMessage, ...],
    ) -> tuple[PromptMessage, ...]:
        return merge_conversation_history(
            base_messages=base_messages,
            conversation_history=conversation_history,
            max_history_turns=self._MAX_HISTORY_TURNS,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

    def _normalize_conversation_history(
        self,
        conversation_history: tuple[PromptMessage, ...],
    ) -> tuple[PromptMessage, ...]:
        return normalize_conversation_history(
            conversation_history=conversation_history,
            max_history_turns=self._MAX_HISTORY_TURNS,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

    def _compact_history_content(self, content: str) -> str:
        return compact_history_content(
            content,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
        )

    def _normalize_goal(self, request_text: str) -> str:
        return normalize_goal(request_text)

    def _build_planning_prompt(
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
        build_config_summary = "none"
        suggested_files = "- none"
        target_file_context = "- none"
        if resolved_repo_path is not None:
            repo_summary = self._inspect_repo_summary(resolved_repo_path)
            repo_summary_text = repo_summary["summary"]
            file_tree_summary = self._build_file_tree_summary(resolved_repo_path)
            build_config_summary = self._build_config_summary(resolved_repo_path)
            target_file_snippets = self._collect_target_file_snippets(
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
            build_config_summary=build_config_summary,
            suggested_files=suggested_files,
            target_file_context=target_file_context,
        )

    def _build_retrieval_observation(self, answer_bundle) -> str:
        return build_retrieval_observation(answer_bundle)

    def _summarize_retrieval(self, answer_bundle) -> str:
        return summarize_retrieval(answer_bundle)

    def _build_recommended_actions(
        self,
        *,
        normalized_goal: str,
        request_text: str,
        answer_bundle,
    ) -> tuple[AgentRuntimeAction, ...]:
        return build_recommended_actions(
            normalized_goal=normalized_goal,
            request_text=request_text,
            answer_bundle=answer_bundle,
        )

    def _render_action_plan(self, actions: tuple[AgentRuntimeAction, ...]) -> str:
        return render_action_plan(actions)

    def _extract_repo_like_paths(self, text: str) -> tuple[str, ...]:
        return extract_repo_like_paths(text)

    def _filter_repo_like_paths(
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
            canonicalize_repo_path_hint=lambda hint, repo_path, files_only_value: self._canonicalize_repo_path_hint(
                hint,
                resolved_repo_path=repo_path,
                files_only=files_only_value,
            ),
        )

    def _execute_recommended_actions(
        self,
        *,
        recommended_actions: tuple[AgentRuntimeAction, ...],
        answer_bundle,
        model: str,
        normalized_goal: str,
        planning_output: str,
        request_text: str,
        scope_dirs: tuple[str, ...],
    ) -> tuple[AgentRuntimeActionExecution, ...]:
        context = build_action_execution_context(
            answer_bundle=answer_bundle,
            model=model,
            request_text=request_text,
            normalized_goal=normalized_goal,
            planning_output=planning_output,
            scope_dirs=scope_dirs,
            resolve_repo_path=lambda goal, text, dirs, citations: self._resolve_repo_path(
                normalized_goal=goal,
                request_text=text,
                scope_dirs=dirs,
                citations=citations,
            ),
            inspect_repo_summary=self._inspect_repo_summary,
            build_config_summary=self._build_config_summary,
            collect_target_file_snippets=lambda repo_path, text, plan: self._collect_target_file_snippets(
                resolved_repo_path=repo_path,
                request_text=text,
                planning_output=plan,
            ),
        )
        executions: list[AgentRuntimeActionExecution] = []
        for action in recommended_actions:
            executions.append(
                self._tool_registry.execute(
                    action,
                    context=context,
                )
            )
        return tuple(executions)

    def _render_action_executions(
        self,
        executions: tuple[AgentRuntimeActionExecution, ...],
    ) -> str:
        return render_action_executions(executions)

    def _compact_excerpt(self, content: str, *, limit: int = 220) -> str:
        return compact_excerpt(content, limit=limit)

    def _build_tool_registry(self) -> AgentToolRegistry:
        return build_agent_tool_registry(
            vault_root=self._knowledge_service.vault_root,
            ollama_client=self._ollama_client,
            compact_excerpt=self._compact_excerpt,
            build_file_tree_summary=self._build_file_tree_summary,
            build_config_summary=self._build_config_summary,
            build_module_draft_prompt=self._build_module_draft_prompt,
            build_patch_plan_prompt=self._build_patch_plan_prompt,
            action_generation_options=self._action_generation_options,
            build_validation_plan=self._build_validation_plan,
            recommend_validation_commands=self._recommend_validation_commands,
        )

    def _is_high_risk_planning_model(self, model: str) -> bool:
        return is_high_risk_planning_model(
            model,
            high_risk_prefixes=self._HIGH_RISK_PLANNING_MODELS,
        )

    def _planning_generation_options(self, model: str) -> dict[str, object]:
        return planning_generation_options(
            model,
            high_risk_prefixes=self._HIGH_RISK_PLANNING_MODELS,
        )

    def _critique_generation_options(self, model: str) -> dict[str, object]:
        return critique_generation_options(
            model,
            high_risk_prefixes=self._HIGH_RISK_PLANNING_MODELS,
        )

    def _refinement_generation_options(self, model: str) -> dict[str, object]:
        return refinement_generation_options(
            model,
            high_risk_prefixes=self._HIGH_RISK_PLANNING_MODELS,
        )

    def _action_generation_options(self, model: str) -> dict[str, object]:
        return action_generation_options(
            model,
            high_risk_prefixes=self._HIGH_RISK_PLANNING_MODELS,
        )

    def _resolve_repo_path(
        self,
        *,
        normalized_goal: str,
        request_text: str,
        scope_dirs: tuple[str, ...],
        citations: tuple[str, ...],
    ) -> Path | None:
        return resolve_repo_path(
            vault_root=self._knowledge_service.vault_root,
            normalized_goal=normalized_goal,
            request_text=request_text,
            scope_dirs=scope_dirs,
            citations=citations,
        )

    def _inspect_repo_summary(self, repo_path: Path) -> dict[str, str]:
        return inspect_repo_summary(
            repo_path,
            vault_root=self._knowledge_service.vault_root,
        )

    def _build_validation_plan(
        self,
        repo_summary: dict[str, str],
        build_config_summary: str | None,
    ) -> str:
        return build_validation_plan(
            repo_summary,
            build_config_summary,
        )

    def _recommend_validation_commands(
        self,
        *,
        repo_summary: dict[str, str],
        build_config_summary: str | None,
    ) -> list[str]:
        return recommend_validation_commands(
            repo_summary=repo_summary,
            build_config_summary=build_config_summary,
        )

    def _build_file_tree_summary(self, repo_path: Path) -> str:
        return build_file_tree_summary(
            repo_path,
            vault_root=self._knowledge_service.vault_root,
        )

    def _build_config_summary(self, repo_path: Path) -> str:
        return build_config_summary(
            repo_path,
            vault_root=self._knowledge_service.vault_root,
        )

    def _build_module_draft_prompt(
        self,
        action: AgentRuntimeAction,
        context: AgentToolContext,
    ) -> str:
        return build_module_draft_action_prompt(
            action=action,
            context=context,
            build_file_tree_summary=self._build_file_tree_summary,
            excerpt_builder=lambda content, limit: self._compact_excerpt(
                content,
                limit=limit,
            ),
            find_repo_files=self._find_repo_files_for_context,
            build_validation_plan=self._build_validation_plan,
            filter_repo_like_paths=self._filter_repo_like_paths,
        )

    def _build_patch_plan_prompt(
        self,
        action: AgentRuntimeAction,
        context: AgentToolContext,
    ) -> str:
        return build_patch_plan_action_prompt(
            action=action,
            context=context,
            build_file_tree_summary=self._build_file_tree_summary,
            excerpt_builder=lambda content, limit: self._compact_excerpt(
                content,
                limit=limit,
            ),
            find_repo_files=self._find_repo_files_for_context,
            build_validation_plan=self._build_validation_plan,
        )

    def _suggest_first_slice_files(
        self,
        action: AgentRuntimeAction,
        context: AgentToolContext,
    ) -> str:
        return render_file_list(self._suggest_first_slice_file_paths(action, context))

    def _suggest_first_slice_file_paths(
        self,
        action: AgentRuntimeAction,
        context: AgentToolContext,
    ) -> tuple[str, ...]:
        return suggest_first_slice_file_paths(
            action_target=action.target,
            request_text=context.request_text,
            resolved_repo_path=context.resolved_repo_path,
            find_repo_files=self._find_repo_files_for_context,
        )

    def _find_repo_files_for_context(
        self,
        repo_path: Path,
        contains: str,
        limit: int,
    ) -> list[str]:
        return self._find_repo_files(
            repo_path,
            contains=contains,
            limit=limit,
        )

    def _find_repo_files(
        self,
        repo_path: Path,
        *,
        contains: str,
        limit: int,
    ) -> list[str]:
        return find_repo_files(
            repo_path,
            vault_root=self._knowledge_service.vault_root,
            contains=contains,
            limit=limit,
        )

    def _collect_target_file_snippets(
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
            vault_root=self._knowledge_service.vault_root,
            extract_repo_like_paths=self._extract_repo_like_paths,
        )

    def _canonicalize_repo_path_hint(
        self,
        path_hint: str,
        *,
        resolved_repo_path: Path | None,
        files_only: bool,
    ) -> str | None:
        return canonicalize_repo_path_hint(
            path_hint,
            vault_root=self._knowledge_service.vault_root,
            resolved_repo_path=resolved_repo_path,
            files_only=files_only,
        )

    def _read_file_snippet(self, file_path: Path, *, max_lines: int = 40, max_chars: int = 1600) -> str:
        return read_file_snippet(
            file_path,
            max_lines=max_lines,
            max_chars=max_chars,
        )

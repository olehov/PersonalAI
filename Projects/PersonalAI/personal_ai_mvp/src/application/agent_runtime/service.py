"""Planning-oriented agent runtime for project-scale coding requests."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from time import perf_counter

from application.agent_runtime.tool_registry import (
    AgentToolRegistry,
)
from application.agent_runtime.instruction_set import (
    AGENT_RUNTIME_SYSTEM_PROMPT,
)
from application.agent_runtime.prompts import (
    build_structured_plan_fallback_from_prompt,
    build_planning_prompt,
    build_retrieval_observation,
    build_system_prompt,
    compact_excerpt,
    extract_plan_lines,
    parse_planning_sections,
    render_target_file_context,
    summarize_retrieval,
)
from application.agent_runtime.action_context import (
    render_file_list,
    suggest_first_slice_file_paths,
)
from application.agent_runtime.action_prompts import (
    build_module_draft_action_prompt,
    build_patch_plan_action_prompt,
)
from application.agent_runtime.artifacts import build_runtime_artifact
from application.agent_runtime.planning import (
    build_recommended_actions,
    build_task_plan,
    render_action_plan,
)
from application.agent_runtime.service_action_support import (
    AgentRuntimeActionSupport,
)
from application.agent_runtime.tool_registry_builder import (
    build_agent_tool_registry,
)
from application.agent_runtime.service_discussion_support import (
    AgentRuntimeDiscussionSupport,
)
from application.agent_runtime.service_repo_support import AgentRuntimeRepoSupport
from application.knowledge.answer_service import AnswerService
from application.knowledge.knowledge_service import KnowledgeService
from domain.models import (
    AgentRuntimeAction,
    AgentRuntimeArtifact,
    PromptMessage,
)
from infrastructure.llm.model_client import ModelClient


@dataclass(frozen=True, slots=True)
class _PlanningPhaseResult:
    normalized_goal: str
    answer_bundle: object
    planner_model: str
    executor_model: str
    critic_model: str | None
    synthesis_model: str | None
    approver_model: str | None
    resolved_discussion_preset: str | None
    retrieval_observation: str
    planning_prompt: str
    planning_output: str
    discussion_trace: object


@dataclass(frozen=True, slots=True)
class _ActionPhaseResult:
    recommended_actions: tuple[AgentRuntimeAction, ...]
    action_executions: tuple[object, ...]
    task_plan: object
    action_plan_text: str
    action_execution_text: str


class AgentRuntimeService:
    """Runs a minimal agent-style loop for large coding requests."""

    _MAX_HISTORY_TURNS = 8
    _MAX_HISTORY_CHARS_PER_MESSAGE = 1_200
    _RECURSIVE_REFINEMENT_REASONING_MODES = {"high"}
    _HIGH_RISK_PLANNING_MODELS = ("deepseek-r1",)
    _RESOURCE_HEAVY_SINGLE_MODEL_PREFIXES = ("gpt-oss",)
    _DISCUSSION_PRESET_MODELS = {
        "fast": ("gemma:latest", "gemma:latest"),
        "coder_critic": ("gemma:latest", "deepseek-r1:8b"),
        "heavy_synthesis": ("qwen2.5-coder:7b", "deepseek-r1:8b"),
    }
    _DEFAULT_DISCUSSION_PRESET_BY_REASONING_MODE = {
        "high": "heavy_synthesis",
        "standard": "coder_critic",
    }

    SYSTEM_PROMPT = AGENT_RUNTIME_SYSTEM_PROMPT

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        answer_service: AnswerService,
        ollama_client: ModelClient,
        history_repository=None,
        recursive_refinement_enabled: bool | None = None,
    ) -> None:
        self._knowledge_service = knowledge_service
        self._answer_service = answer_service
        self._ollama_client = ollama_client
        self._history_repository = history_repository
        self._recursive_refinement_enabled = (
            AgentRuntimeDiscussionSupport.default_recursive_refinement_enabled()
            if recursive_refinement_enabled is None
            else recursive_refinement_enabled
        )
        self._discussion_support = AgentRuntimeDiscussionSupport(
            ollama_client=self._ollama_client,
            system_prompt=self.SYSTEM_PROMPT,
            max_history_turns=self._MAX_HISTORY_TURNS,
            max_history_chars_per_message=self._MAX_HISTORY_CHARS_PER_MESSAGE,
            recursive_refinement_reasoning_modes=self._RECURSIVE_REFINEMENT_REASONING_MODES,
            high_risk_planning_models=self._HIGH_RISK_PLANNING_MODELS,
            resource_heavy_single_model_prefixes=self._RESOURCE_HEAVY_SINGLE_MODEL_PREFIXES,
            discussion_preset_models=self._DISCUSSION_PRESET_MODELS,
            default_discussion_preset_by_reasoning_mode=self._DEFAULT_DISCUSSION_PRESET_BY_REASONING_MODE,
            recursive_refinement_enabled=self._recursive_refinement_enabled,
        )
        self._repo_support = AgentRuntimeRepoSupport(
            vault_root=self._knowledge_service.vault_root,
        )
        self._tool_registry = self._build_tool_registry()
        self._action_support = AgentRuntimeActionSupport(
            tool_registry=self._tool_registry,
            repo_support=self._repo_support,
            multi_model_discussion_enabled=self._discussion_support.multi_model_discussion_enabled,
        )

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
        planning_phase = self._run_planning_phase(
            request_text=request_text,
            model=model,
            scope_dirs=scope_dirs,
            conversation_history=conversation_history,
            discussion_preset=discussion_preset,
            reasoning_mode=reasoning_mode,
        )
        action_phase = self._run_action_phase(
            request_text=request_text,
            scope_dirs=scope_dirs,
            planning_phase=planning_phase,
        )
        artifact = self._build_runtime_artifact(
            scope_dirs=scope_dirs,
            request_text=request_text,
            planning_phase=planning_phase,
            action_phase=action_phase,
        )
        return self._persist_artifact(artifact, started_at=started_at)

    def _run_planning_phase(
        self,
        *,
        request_text: str,
        model: str,
        scope_dirs: tuple[str, ...],
        conversation_history: tuple[PromptMessage, ...],
        discussion_preset: str | None,
        reasoning_mode: str,
    ) -> _PlanningPhaseResult:
        normalized_goal = self._discussion_support.normalize_goal(request_text)
        answer_bundle = self._answer_service.prepare_answer(
            normalized_goal,
            scope_dirs=scope_dirs,
            reasoning_mode=reasoning_mode,
        )
        (
            planner_model,
            executor_model,
            critic_model,
            synthesis_model,
            approver_model,
            resolved_discussion_preset,
        ) = self._discussion_support.resolve_role_models(
            model,
            discussion_preset=discussion_preset,
            reasoning_mode=reasoning_mode,
            task_mode=answer_bundle.task_mode,
        )
        resolved_repo_path = self._repo_support.resolve_repo_path(
            normalized_goal=normalized_goal,
            request_text=request_text,
            citations=answer_bundle.citations,
            scope_dirs=scope_dirs,
        )
        retrieval_observation = self._build_retrieval_observation(answer_bundle)
        planning_prompt = self._repo_support.build_planning_prompt(
            request_text=request_text,
            normalized_goal=normalized_goal,
            answer_bundle=answer_bundle,
            retrieval_observation=retrieval_observation,
            reasoning_mode=reasoning_mode,
            resolved_repo_path=resolved_repo_path,
        )
        planning_messages = self._discussion_support.merge_conversation_history(
            (
                PromptMessage(role="system", content=self._discussion_support.build_system_prompt(reasoning_mode)),
                PromptMessage(role="user", content=planning_prompt),
            ),
            conversation_history,
        )
        planning_output, discussion_trace = self._discussion_support.generate_planning_output(
            model=planner_model,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            approver_model=approver_model,
            messages=planning_messages,
            reasoning_mode=reasoning_mode,
            discussion_preset=resolved_discussion_preset,
        )
        planning_output, discussion_trace = self._repair_planning_output_if_needed(
            planning_output=planning_output,
            planning_prompt=planning_prompt,
            discussion_trace=discussion_trace,
        )
        return _PlanningPhaseResult(
            normalized_goal=normalized_goal,
            answer_bundle=answer_bundle,
            planner_model=planner_model,
            executor_model=executor_model,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            approver_model=approver_model,
            resolved_discussion_preset=resolved_discussion_preset,
            retrieval_observation=retrieval_observation,
            planning_prompt=planning_prompt,
            planning_output=planning_output,
            discussion_trace=discussion_trace,
        )

    def _repair_planning_output_if_needed(
        self,
        *,
        planning_output: str,
        planning_prompt: str,
        discussion_trace,
    ) -> tuple[str, object]:
        if planning_output.startswith("Goal") and len(self._parse_planning_sections(planning_output)) >= 8:
            return planning_output, discussion_trace
        repaired_output = build_structured_plan_fallback_from_prompt(planning_prompt)
        if discussion_trace is None:
            return repaired_output, discussion_trace
        return repaired_output, replace(
            discussion_trace,
            synthesis_output=repaired_output,
            fallback_used=(
                discussion_trace.fallback_used or "service_level_structured_plan_fallback"
            ),
        )

    def _run_action_phase(
        self,
        *,
        request_text: str,
        scope_dirs: tuple[str, ...],
        planning_phase: _PlanningPhaseResult,
    ) -> _ActionPhaseResult:
        recommended_actions = self._build_recommended_actions(
            normalized_goal=planning_phase.normalized_goal,
            request_text=request_text,
            answer_bundle=planning_phase.answer_bundle,
        )
        action_executions = self._action_support.execute_recommended_actions(
            recommended_actions=recommended_actions,
            answer_bundle=planning_phase.answer_bundle,
            model=planning_phase.executor_model,
            critic_model=planning_phase.critic_model,
            synthesis_model=planning_phase.synthesis_model,
            approver_model=planning_phase.approver_model,
            discussion_preset=planning_phase.resolved_discussion_preset,
            normalized_goal=planning_phase.normalized_goal,
            planning_output=planning_phase.planning_output,
            request_text=request_text,
            scope_dirs=scope_dirs,
        )
        task_plan = self._build_task_plan(
            normalized_goal=planning_phase.normalized_goal,
            planning_output=planning_phase.planning_output,
            recommended_actions=recommended_actions,
        )
        action_plan_text = self._render_action_plan(recommended_actions)
        action_execution_text = self._action_support.render_action_executions(action_executions)
        return _ActionPhaseResult(
            recommended_actions=recommended_actions,
            action_executions=action_executions,
            task_plan=task_plan,
            action_plan_text=action_plan_text,
            action_execution_text=action_execution_text,
        )

    def _build_runtime_artifact(
        self,
        *,
        scope_dirs: tuple[str, ...],
        request_text: str,
        planning_phase: _PlanningPhaseResult,
        action_phase: _ActionPhaseResult,
    ) -> AgentRuntimeArtifact:
        return build_runtime_artifact(
            planner_model=planning_phase.planner_model,
            executor_model=planning_phase.executor_model,
            critic_model=planning_phase.critic_model,
            synthesis_model=planning_phase.synthesis_model,
            approver_model=planning_phase.approver_model,
            discussion_preset=planning_phase.resolved_discussion_preset,
            discussion_trace=planning_phase.discussion_trace,
            request_text=request_text,
            normalized_goal=planning_phase.normalized_goal,
            task_mode=planning_phase.answer_bundle.task_mode,
            scope_dirs=scope_dirs,
            citations=planning_phase.answer_bundle.citations,
            retrieval_summary=self._summarize_retrieval(planning_phase.answer_bundle),
            retrieval_observation=planning_phase.retrieval_observation,
            planning_prompt=planning_phase.planning_prompt,
            planning_output=planning_phase.planning_output,
            recommended_actions=action_phase.recommended_actions,
            action_plan_text=action_phase.action_plan_text,
            action_executions=action_phase.action_executions,
            action_execution_text=action_phase.action_execution_text,
            task_plan=action_phase.task_plan,
            prompt=planning_phase.answer_bundle,
        )

    def _persist_artifact(
        self,
        artifact: AgentRuntimeArtifact,
        *,
        started_at: float,
    ) -> AgentRuntimeArtifact:
        if self._history_repository is None:
            return artifact
        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        history_entry = self._history_repository.save_agent_runtime_artifact(
            artifact,
            latency_ms=latency_ms,
        )
        if history_entry is not None and getattr(history_entry, "entry_id", None) is not None:
            return replace(artifact, history_entry_id=history_entry.entry_id)
        return artifact

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

    def _build_tool_registry(self) -> AgentToolRegistry:
        return build_agent_tool_registry(
            vault_root=self._knowledge_service.vault_root,
            ollama_client=self._ollama_client,
            compact_excerpt=self._repo_support.compact_excerpt,
            build_file_tree_summary=self._repo_support.build_file_tree_summary,
            build_config_summary=self._repo_support.build_config_summary,
            build_module_draft_prompt=self._repo_support.build_module_draft_prompt,
            build_patch_plan_prompt=self._repo_support.build_patch_plan_prompt,
            action_generation_options=self._discussion_support.action_generation_options,
            build_validation_plan=self._repo_support.build_validation_plan,
            recommend_validation_commands=self._repo_support.recommend_validation_commands,
        )

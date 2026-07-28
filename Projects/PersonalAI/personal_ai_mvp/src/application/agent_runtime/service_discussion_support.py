"""Discussion, model-resolution, and history helpers for AgentRuntimeService."""

from __future__ import annotations

from application.agent_runtime.generation import generate_planning_output
from application.agent_runtime.model_options import (
    action_generation_options,
    critique_generation_options,
    is_high_risk_planning_model,
    planning_generation_options,
    refinement_generation_options,
)
from application.agent_runtime.planning import (
    build_recursive_critique_messages,
    build_recursive_refinement_messages,
    compact_history_content,
    merge_conversation_history,
    normalize_conversation_history,
    normalize_goal,
)
from application.agent_runtime.prompts import build_system_prompt
from infrastructure.config.settings import get_settings


class AgentRuntimeDiscussionSupport:
    """Owns model-role resolution and planning-discussion support logic."""

    def __init__(
        self,
        *,
        ollama_client,
        system_prompt: str,
        max_history_turns: int,
        max_history_chars_per_message: int,
        recursive_refinement_reasoning_modes: set[str],
        high_risk_planning_models: tuple[str, ...],
        resource_heavy_single_model_prefixes: tuple[str, ...],
        discussion_preset_models: dict[str, tuple[str, str]],
        default_discussion_preset_by_reasoning_mode: dict[str, str],
        recursive_refinement_enabled: bool | None = None,
    ) -> None:
        self._ollama_client = ollama_client
        self._system_prompt = system_prompt
        self._max_history_turns = max_history_turns
        self._max_history_chars_per_message = max_history_chars_per_message
        self._recursive_refinement_reasoning_modes = recursive_refinement_reasoning_modes
        self._high_risk_planning_models = high_risk_planning_models
        self._resource_heavy_single_model_prefixes = resource_heavy_single_model_prefixes
        self._discussion_preset_models = discussion_preset_models
        self._default_discussion_preset_by_reasoning_mode = (
            default_discussion_preset_by_reasoning_mode
        )
        self._recursive_refinement_enabled = (
            self.default_recursive_refinement_enabled()
            if recursive_refinement_enabled is None
            else recursive_refinement_enabled
        )
        self._multi_model_discussion_enabled = self.default_multi_model_discussion_enabled()

    @property
    def recursive_refinement_enabled(self) -> bool:
        return self._recursive_refinement_enabled

    @property
    def multi_model_discussion_enabled(self) -> bool:
        return self._multi_model_discussion_enabled

    def resolve_role_models(
        self,
        requested_model: str,
        *,
        discussion_preset: str | None,
        reasoning_mode: str,
        task_mode: str,
    ) -> tuple[str, str, str | None, str | None, str | None, str | None]:
        """Resolve planner/executor/discussion models from env overrides with safe fallbacks."""
        settings = get_settings()
        normalized_preset = self.resolve_discussion_preset(
            discussion_preset=discussion_preset,
            reasoning_mode=reasoning_mode,
            task_mode=task_mode,
        )
        planner_override = settings.agent_planner_model
        if normalized_preset in self._discussion_preset_models:
            preset_critic, preset_synthesis = self._discussion_preset_models[normalized_preset]
            planner_model = planner_override or requested_model.strip()
            critic_model = preset_critic
            synthesis_model = preset_synthesis
        else:
            planner_model = planner_override or requested_model.strip()
            critic_model = settings.agent_critic_model
            synthesis_model = settings.agent_synthesis_model
        if self.requires_single_model_discussion(planner_model):
            critic_model = planner_model
            synthesis_model = planner_model
            normalized_preset = "resource_safe_single_model"
        executor_model = settings.agent_executor_model or planner_model
        approver_model = settings.agent_approver_model or synthesis_model or planner_model
        return (
            planner_model,
            executor_model,
            critic_model,
            synthesis_model,
            approver_model,
            normalized_preset,
        )

    def resolve_discussion_preset(
        self,
        *,
        discussion_preset: str | None,
        reasoning_mode: str,
        task_mode: str,
    ) -> str | None:
        normalized_preset = (discussion_preset or "").strip().lower() or None
        if normalized_preset in self._discussion_preset_models:
            return normalized_preset

        settings = get_settings()
        env_preset = settings.agent_discussion_preset
        if env_preset in self._discussion_preset_models:
            return env_preset

        if not self._multi_model_discussion_enabled:
            return None

        critic_override = settings.agent_critic_model or ""
        synthesis_override = settings.agent_synthesis_model or ""
        if critic_override or synthesis_override:
            return "custom"

        default_preset = self._default_discussion_preset_by_reasoning_mode.get(reasoning_mode)
        if default_preset is not None:
            return default_preset
        if task_mode == "implementation":
            return "coder_critic"
        return "fast"

    def requires_single_model_discussion(self, model: str) -> bool:
        normalized = model.strip().casefold()
        return any(prefix in normalized for prefix in self._resource_heavy_single_model_prefixes)

    def generate_planning_output(
        self,
        *,
        model: str,
        critic_model: str | None,
        synthesis_model: str | None,
        approver_model: str | None,
        messages,
        reasoning_mode: str,
        discussion_preset: str | None,
    ):
        return generate_planning_output(
            ollama_client=self._ollama_client,
            model=model,
            messages=messages,
            reasoning_mode=reasoning_mode,
            discussion_preset=discussion_preset,
            recursive_refinement_enabled=self._recursive_refinement_enabled,
            recursive_refinement_reasoning_modes=self._recursive_refinement_reasoning_modes,
            multi_model_discussion_enabled=self._multi_model_discussion_enabled,
            critic_model=critic_model,
            synthesis_model=synthesis_model,
            approver_model=approver_model,
            planning_generation_options=self.planning_generation_options,
            critique_generation_options=self.critique_generation_options,
            refinement_generation_options=self.refinement_generation_options,
            build_recursive_critique_messages=self.build_recursive_critique_messages,
            build_recursive_refinement_messages=self.build_recursive_refinement_messages,
        )

    def build_recursive_critique_messages(
        self,
        *,
        base_messages,
        draft_text: str,
    ):
        return build_recursive_critique_messages(
            base_messages=base_messages,
            draft_text=draft_text,
        )

    def build_recursive_refinement_messages(
        self,
        *,
        base_messages,
        draft_text: str,
        critique_text: str,
    ):
        return build_recursive_refinement_messages(
            base_messages=base_messages,
            draft_text=draft_text,
            critique_text=critique_text,
        )

    @staticmethod
    def default_recursive_refinement_enabled() -> bool:
        """Resolve whether recursive planning refinement is enabled from the environment."""
        return get_settings().agent_recursive_refinement

    @staticmethod
    def default_multi_model_discussion_enabled() -> bool:
        """Resolve whether planner/critic/synthesizer discussion is enabled."""
        return get_settings().agent_multi_model_discussion

    def build_system_prompt(self, reasoning_mode: str) -> str:
        return build_system_prompt(self._system_prompt, reasoning_mode)

    def merge_conversation_history(
        self,
        base_messages,
        conversation_history,
    ):
        return merge_conversation_history(
            base_messages=base_messages,
            conversation_history=conversation_history,
            max_history_turns=self._max_history_turns,
            max_history_chars_per_message=self._max_history_chars_per_message,
        )

    def normalize_conversation_history(self, conversation_history):
        return normalize_conversation_history(
            conversation_history=conversation_history,
            max_history_turns=self._max_history_turns,
            max_history_chars_per_message=self._max_history_chars_per_message,
        )

    def compact_history_content(self, content: str) -> str:
        return compact_history_content(
            content,
            max_history_chars_per_message=self._max_history_chars_per_message,
        )

    @staticmethod
    def normalize_goal(request_text: str) -> str:
        return normalize_goal(request_text)

    def is_high_risk_planning_model(self, model: str) -> bool:
        return is_high_risk_planning_model(
            model,
            high_risk_prefixes=self._high_risk_planning_models,
        )

    def planning_generation_options(self, model: str) -> dict[str, object]:
        return planning_generation_options(
            model,
            high_risk_prefixes=self._high_risk_planning_models,
        )

    def critique_generation_options(self, model: str) -> dict[str, object]:
        return critique_generation_options(
            model,
            high_risk_prefixes=self._high_risk_planning_models,
        )

    def refinement_generation_options(self, model: str) -> dict[str, object]:
        return refinement_generation_options(
            model,
            high_risk_prefixes=self._high_risk_planning_models,
        )

    def action_generation_options(self, model: str) -> dict[str, object]:
        return action_generation_options(
            model,
            high_risk_prefixes=self._high_risk_planning_models,
        )

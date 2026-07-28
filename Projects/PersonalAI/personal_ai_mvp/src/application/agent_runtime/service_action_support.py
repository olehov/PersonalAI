"""Action-execution support helpers for AgentRuntimeService."""

from __future__ import annotations

from application.agent_runtime.execution_context import (
    build_action_execution_context,
)
from application.agent_runtime.planning import render_action_executions


class AgentRuntimeActionSupport:
    """Owns action-model fallback, execution context building, and action runs."""

    def __init__(
        self,
        *,
        tool_registry,
        repo_support,
        multi_model_discussion_enabled: bool,
    ) -> None:
        self._tool_registry = tool_registry
        self._repo_support = repo_support
        self._multi_model_discussion_enabled = multi_model_discussion_enabled

    @staticmethod
    def resolve_action_critic_model(
        *,
        executor_model: str,
        critic_model: str | None,
    ) -> str | None:
        return critic_model or executor_model

    @staticmethod
    def resolve_action_synthesis_model(
        *,
        executor_model: str,
        synthesis_model: str | None,
    ) -> str | None:
        return synthesis_model or executor_model

    @staticmethod
    def resolve_action_approver_model(
        *,
        executor_model: str,
        approver_model: str | None,
    ) -> str | None:
        return approver_model or executor_model

    def execute_recommended_actions(
        self,
        *,
        recommended_actions,
        answer_bundle,
        model: str,
        critic_model: str | None,
        synthesis_model: str | None,
        approver_model: str | None,
        discussion_preset: str | None,
        normalized_goal: str,
        planning_output: str,
        request_text: str,
        scope_dirs: tuple[str, ...],
    ):
        """Execute each recommended action with one shared execution context."""
        context = build_action_execution_context(
            answer_bundle=answer_bundle,
            model=model,
            critic_model=self.resolve_action_critic_model(
                executor_model=model,
                critic_model=critic_model,
            ),
            synthesis_model=self.resolve_action_synthesis_model(
                executor_model=model,
                synthesis_model=synthesis_model,
            ),
            approver_model=self.resolve_action_approver_model(
                executor_model=model,
                approver_model=approver_model,
            ),
            discussion_preset=discussion_preset,
            multi_model_discussion_enabled=self._multi_model_discussion_enabled,
            request_text=request_text,
            normalized_goal=normalized_goal,
            planning_output=planning_output,
            scope_dirs=scope_dirs,
            resolve_repo_path=lambda goal, text, dirs, citations: self._repo_support.resolve_repo_path(
                normalized_goal=goal,
                request_text=text,
                scope_dirs=dirs,
                citations=citations,
            ),
            inspect_repo_summary=self._repo_support.inspect_repo_summary,
            build_config_summary=self._repo_support.build_config_summary,
            collect_target_file_snippets=lambda repo_path, text, plan: self._repo_support.collect_target_file_snippets(
                resolved_repo_path=repo_path,
                request_text=text,
                planning_output=plan,
            ),
        )
        executions = [
            self._tool_registry.execute(
                action,
                context=context,
            )
            for action in recommended_actions
        ]
        return tuple(executions)

    @staticmethod
    def render_action_executions(executions) -> str:
        """Render executed action artifacts for the final runtime output."""
        return render_action_executions(executions)

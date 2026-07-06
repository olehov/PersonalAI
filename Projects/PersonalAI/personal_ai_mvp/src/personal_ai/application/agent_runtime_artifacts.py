"""Artifact-building helpers for the agent runtime."""

from __future__ import annotations

from personal_ai.domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    AgentRuntimeArtifact,
    AgentRuntimeStep,
)


def build_runtime_artifact(
    *,
    planner_model: str,
    executor_model: str,
    critic_model: str | None,
    synthesis_model: str | None,
    discussion_preset: str | None,
    discussion_trace,
    request_text: str,
    normalized_goal: str,
    task_mode: str,
    scope_dirs: tuple[str, ...],
    citations: tuple[str, ...],
    retrieval_summary: str,
    retrieval_observation: str,
    planning_prompt: str,
    planning_output: str,
    recommended_actions: tuple[AgentRuntimeAction, ...],
    action_plan_text: str,
    action_executions: tuple[AgentRuntimeActionExecution, ...],
    action_execution_text: str,
    task_plan,
    prompt,
) -> AgentRuntimeArtifact:
    """Build the stable runtime artifact payload from prepared runtime pieces."""
    return AgentRuntimeArtifact(
        model=planner_model,
        request_text=request_text,
        normalized_goal=normalized_goal,
        task_mode=task_mode,
        status="needs_execution_layer",
        executor_model=executor_model,
        critic_model=critic_model,
        synthesis_model=synthesis_model,
        discussion_preset=discussion_preset,
        discussion_trace=discussion_trace,
        scope_dirs=scope_dirs,
        citations=citations,
        steps=(
            AgentRuntimeStep(
                step_index=1,
                kind="retrieval",
                title="Grounded Retrieval",
                input_text=normalized_goal,
                output_text=retrieval_summary,
                observation=retrieval_observation,
            ),
            AgentRuntimeStep(
                step_index=2,
                kind="planning",
                title="Implementation Slice Planning",
                input_text=planning_prompt,
                output_text=planning_output,
                observation=(
                    "Planning completed from grounded vault context. "
                    "No filesystem writes, shell commands, or tests were executed in this runtime slice."
                ),
            ),
            AgentRuntimeStep(
                step_index=3,
                kind="action_plan",
                title="Safe Action Plan",
                input_text=normalized_goal,
                output_text=action_plan_text,
                observation=(
                    "Recommended actions were derived without execution. "
                    "These actions are safe candidates for a future tool/execution layer."
                ),
            ),
            AgentRuntimeStep(
                step_index=4,
                kind="action_execution",
                title="Safe Action Execution",
                input_text=action_plan_text,
                output_text=action_execution_text,
                observation=(
                    "Only safe in-process actions and whitelist validation commands were executed. "
                    "Direct source mutation still requires a separate controlled execution layer."
                ),
            ),
        ),
        recommended_actions=recommended_actions,
        action_executions=action_executions,
        task_plan=task_plan,
        final_output=planning_output,
        prompt=prompt,
    )

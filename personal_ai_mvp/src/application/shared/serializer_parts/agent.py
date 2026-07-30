"""Agent runtime serializers."""

from __future__ import annotations

from domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    AgentRuntimeArtifact,
    AgentRuntimeStep,
    AgentRuntimeTaskPlan,
    AgentRuntimeTaskPlanEntry,
)
from application.shared.serializer_parts.core import serialize_answer_bundle


def serialize_agent_runtime_step(step: AgentRuntimeStep) -> dict[str, object]:
    return {
        "step_index": step.step_index,
        "kind": step.kind,
        "title": step.title,
        "input_text": step.input_text,
        "output_text": step.output_text,
        "observation": step.observation,
    }


def serialize_agent_runtime_action(action: AgentRuntimeAction) -> dict[str, object]:
    return {
        "action_type": action.action_type,
        "title": action.title,
        "target": action.target,
        "instruction": action.instruction,
        "rationale": action.rationale,
    }


def serialize_agent_runtime_action_execution(
    execution: AgentRuntimeActionExecution,
) -> dict[str, object]:
    return {
        "action_type": execution.action_type,
        "target": execution.target,
        "status": execution.status,
        "output_text": execution.output_text,
    }


def serialize_agent_runtime_task_plan_entry(
    entry: AgentRuntimeTaskPlanEntry,
) -> dict[str, object]:
    return {
        "step_index": entry.step_index,
        "title": entry.title,
        "status": entry.status,
        "details": entry.details,
        "source_section": entry.source_section,
    }


def serialize_agent_runtime_task_plan(
    plan: AgentRuntimeTaskPlan,
) -> dict[str, object]:
    return {
        "goal": plan.goal,
        "current_focus": plan.current_focus,
        "summary": plan.summary,
        "entries": [
            serialize_agent_runtime_task_plan_entry(entry)
            for entry in plan.entries
        ],
        "validation_checks": list(plan.validation_checks),
    }


def serialize_agent_runtime_artifact(artifact: AgentRuntimeArtifact) -> dict[str, object]:
    action_executions = tuple(getattr(artifact, "action_executions", ()))
    recommended_actions = tuple(getattr(artifact, "recommended_actions", ()))
    task_plan = getattr(artifact, "task_plan", None)
    executed_actions = sum(
        1 for execution in action_executions if execution.status == "executed"
    )
    deferred_actions = sum(
        1 for execution in action_executions if execution.status == "deferred"
    )
    failed_actions = sum(
        1 for execution in action_executions if execution.status == "failed"
    )
    return {
        "generated_at": artifact.generated_at.isoformat(),
        "history_entry_id": getattr(artifact, "history_entry_id", None),
        "model": artifact.model,
        "executor_model": getattr(artifact, "executor_model", None),
        "critic_model": getattr(artifact, "critic_model", None),
        "synthesis_model": getattr(artifact, "synthesis_model", None),
        "approver_model": getattr(artifact, "approver_model", None),
        "discussion_preset": getattr(artifact, "discussion_preset", None),
        "request_text": artifact.request_text,
        "normalized_goal": artifact.normalized_goal,
        "task_mode": artifact.task_mode,
        "status": artifact.status,
        "scope_dirs": list(artifact.scope_dirs),
        "citations": list(artifact.citations),
        "overview": {
            "step_count": len(artifact.steps),
            "recommended_action_count": len(recommended_actions),
            "executed_action_count": executed_actions,
            "deferred_action_count": deferred_actions,
            "failed_action_count": failed_actions,
            "citation_count": len(artifact.citations),
            "planned_task_count": len(task_plan.entries) if task_plan is not None else 0,
            "planner_model": artifact.model,
            "executor_model": getattr(artifact, "executor_model", None),
            "critic_model": getattr(artifact, "critic_model", None),
            "synthesis_model": getattr(artifact, "synthesis_model", None),
            "approver_model": getattr(artifact, "approver_model", None),
            "discussion_preset": getattr(artifact, "discussion_preset", None),
        },
        "steps": [serialize_agent_runtime_step(step) for step in artifact.steps],
        "recommended_actions": [
            serialize_agent_runtime_action(action)
            for action in recommended_actions
        ],
        "action_executions": [
            serialize_agent_runtime_action_execution(execution)
            for execution in action_executions
        ],
        "task_plan": (
            serialize_agent_runtime_task_plan(task_plan)
            if task_plan is not None
            else None
        ),
        "discussion_trace": (
            {
                "preset": artifact.discussion_trace.preset,
                "planner_draft": artifact.discussion_trace.planner_draft,
                "critic_feedback": artifact.discussion_trace.critic_feedback,
                "synthesis_output": artifact.discussion_trace.synthesis_output,
                "approver_feedback": artifact.discussion_trace.approver_feedback,
                "approval_status": artifact.discussion_trace.approval_status,
                "planner_revisions": artifact.discussion_trace.planner_revisions,
                "planner_rollbacks": artifact.discussion_trace.planner_rollbacks,
                "fallback_used": artifact.discussion_trace.fallback_used,
            }
            if getattr(artifact, "discussion_trace", None) is not None
            else None
        ),
        "final_output": artifact.final_output,
        "prompt": (
            serialize_answer_bundle(artifact.prompt)
            if artifact.prompt is not None
            else None
        ),
    }

"""Agent runtime domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from domain.model_parts.knowledge import AnswerBundle, AnswerTaskMode


AgentStepKind = Literal["retrieval", "planning", "action_plan", "action_execution"]
AgentRunStatus = Literal["completed", "needs_execution_layer"]
AgentActionExecutionStatus = Literal["executed", "deferred", "failed"]
AgentTaskPlanStatus = Literal["completed", "next", "pending"]


@dataclass(frozen=True, slots=True)
class AgentRuntimeStep:
    """One step inside a lightweight agent-runtime artifact."""

    step_index: int
    kind: AgentStepKind
    title: str
    input_text: str
    output_text: str
    observation: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeAction:
    """A safe machine-readable next action proposed by the runtime."""

    action_type: str
    title: str
    target: str
    instruction: str
    rationale: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeActionExecution:
    """Execution outcome for one recommended runtime action."""

    action_type: str
    target: str
    status: AgentActionExecutionStatus
    output_text: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeTaskPlanEntry:
    """One structured task-plan item extracted from an agent planning run."""

    step_index: int
    title: str
    status: AgentTaskPlanStatus
    details: str
    source_section: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeTaskPlan:
    """Structured task plan surfaced to the UI and future execution layers."""

    goal: str
    current_focus: str
    summary: str
    entries: tuple[AgentRuntimeTaskPlanEntry, ...] = field(default_factory=tuple)
    validation_checks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AgentRuntimeDiscussionTrace:
    """Trace of a multi-model planning discussion."""

    preset: str
    planner_draft: str
    critic_feedback: str | None = None
    synthesis_output: str | None = None
    approver_feedback: str | None = None
    approval_status: str | None = None
    planner_revisions: int = 0
    planner_rollbacks: int = 0
    fallback_used: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRuntimeArtifact:
    """A reviewable artifact produced by the planning-oriented agent runtime."""

    model: str
    request_text: str
    normalized_goal: str
    task_mode: AnswerTaskMode
    status: AgentRunStatus
    executor_model: str | None = None
    critic_model: str | None = None
    synthesis_model: str | None = None
    approver_model: str | None = None
    discussion_preset: str | None = None
    discussion_trace: AgentRuntimeDiscussionTrace | None = None
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    steps: tuple[AgentRuntimeStep, ...] = field(default_factory=tuple)
    recommended_actions: tuple[AgentRuntimeAction, ...] = field(default_factory=tuple)
    action_executions: tuple[AgentRuntimeActionExecution, ...] = field(default_factory=tuple)
    task_plan: AgentRuntimeTaskPlan | None = None
    history_entry_id: int | None = None
    final_output: str = ""
    prompt: AnswerBundle | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

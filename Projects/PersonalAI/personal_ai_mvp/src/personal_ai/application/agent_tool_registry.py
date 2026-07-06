"""Registry and execution contract for safe agent runtime tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from personal_ai.domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
)


@dataclass(frozen=True, slots=True)
class AgentToolContext:
    """Execution context shared by safe agent runtime tools."""

    retrieval_notes: dict[str, object]
    resolved_repo_path: Path | None
    repo_summary: dict[str, str] | None
    build_config_summary: str | None
    model: str
    request_text: str
    normalized_goal: str
    planning_output: str
    citations: tuple[str, ...]
    target_file_snippets: dict[str, str] = field(default_factory=dict)


class AgentToolExecutor(Protocol):
    """Callable contract for a safe runtime tool executor."""

    def __call__(
        self,
        action: AgentRuntimeAction,
        context: AgentToolContext,
    ) -> AgentRuntimeActionExecution:
        """Execute one safe action and return a structured outcome."""


class AgentToolRegistry:
    """Maps agent action types to safe execution adapters."""

    def __init__(self) -> None:
        self._executors: dict[str, AgentToolExecutor] = {}

    def register(self, action_type: str, executor: AgentToolExecutor) -> None:
        """Register a safe executor for one action type."""
        self._executors[action_type] = executor

    def execute(
        self,
        action: AgentRuntimeAction,
        *,
        context: AgentToolContext,
    ) -> AgentRuntimeActionExecution:
        """Execute a registered action or return a deferred outcome."""
        executor = self._executors.get(action.action_type)
        if executor is None:
            return AgentRuntimeActionExecution(
                action_type=action.action_type,
                target=action.target,
                status="deferred",
                output_text=(
                    "This action is planned but not yet connected to a dedicated execution adapter."
                ),
            )
        return executor(action, context)

"""Persisted history entry domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domain.model_parts.agent import AgentRunStatus
from domain.model_parts.knowledge import AnswerTaskMode


@dataclass(frozen=True, slots=True)
class QueryHistoryEntry:
    """Persisted record of a grounded ask/query interaction."""

    entry_id: int
    created_at: datetime
    question: str
    answer_text: str
    model: str
    task_mode: AnswerTaskMode = "general"
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    latency_ms: int | None = None
    prompt_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class AgentRunHistoryEntry:
    """Persisted record of an agent-runtime execution artifact."""

    entry_id: int
    created_at: datetime
    request_text: str
    normalized_goal: str
    model: str
    task_mode: AnswerTaskMode
    status: AgentRunStatus
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    latency_ms: int | None = None
    artifact_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkRunHistoryEntry:
    """Persisted record of one benchmark-pack run artifact."""

    entry_id: int
    created_at: datetime
    pack_id: str
    task_id: str
    category: str
    workflow: str
    model: str
    status: str
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    prompt_text: str = ""
    latency_ms: int | None = None
    result_payload: dict[str, object] | None = None

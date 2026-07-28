"""SQLite-backed persistence for grounded query history."""

from __future__ import annotations

from pathlib import Path

from domain.models import (
    AgentRunHistoryEntry,
    AgentRuntimeArtifact,
    BenchmarkRunHistoryEntry,
    GeneratedAnswer,
    QueryHistoryEntry,
)
from infrastructure.history.rows import (
    row_to_agent_run_entry,
    row_to_benchmark_run_entry,
    row_to_query_entry,
)
from infrastructure.history.repository_support import (
    count_agent_run_rows,
    count_benchmark_run_rows,
    count_query_rows,
    ensure_history_schema,
    list_agent_run_rows,
    list_benchmark_run_rows,
    list_query_rows,
    save_agent_runtime_artifact_row,
    save_benchmark_run_result_row,
    save_generated_answer_row,
    update_agent_runtime_task_plan_row,
)
from infrastructure.history.serialization import (
    serialize_agent_runtime_payload,
    serialize_benchmark_result_payload,
    serialize_prompt_payload,
)

DEFAULT_QUERY_HISTORY_RETENTION = 200
DEFAULT_AGENT_RUN_HISTORY_RETENTION = 120
DEFAULT_BENCHMARK_HISTORY_RETENTION = 200


class SQLiteQueryHistoryRepository:
    """Stores grounded ask interactions in a local SQLite database."""

    def __init__(
        self,
        database_path: Path,
        *,
        query_history_retention: int = DEFAULT_QUERY_HISTORY_RETENTION,
        agent_run_history_retention: int = DEFAULT_AGENT_RUN_HISTORY_RETENTION,
        benchmark_history_retention: int = DEFAULT_BENCHMARK_HISTORY_RETENTION,
    ) -> None:
        self._database_path = database_path
        self._query_history_retention = max(1, query_history_retention)
        self._agent_run_history_retention = max(1, agent_run_history_retention)
        self._benchmark_history_retention = max(1, benchmark_history_retention)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_history_schema(self._database_path)

    @property
    def database_path(self) -> Path:
        """Returns the backing SQLite file path."""
        return self._database_path

    def save_generated_answer(
        self,
        answer: GeneratedAnswer,
        *,
        scope_dirs: tuple[str, ...] = (),
        latency_ms: int | None = None,
    ) -> QueryHistoryEntry:
        """Persist a generated answer and return the created history entry."""
        task_mode = answer.prompt.task_mode if answer.prompt is not None else "general"
        prompt_payload = serialize_prompt_payload(answer.prompt)
        entry_id, created_at = save_generated_answer_row(
            self._database_path,
            answer=answer,
            task_mode=task_mode,
            prompt_payload=prompt_payload,
            scope_dirs=scope_dirs,
            latency_ms=latency_ms,
            retention_limit=self._query_history_retention,
        )

        return QueryHistoryEntry(
            entry_id=entry_id,
            created_at=created_at,
            question=answer.question,
            answer_text=answer.answer_text,
            model=answer.model,
            task_mode=task_mode,
            scope_dirs=tuple(scope_dirs),
            citations=answer.citations,
            latency_ms=latency_ms,
            prompt_payload=prompt_payload,
        )

    def list_entries(self, *, limit: int = 20) -> list[QueryHistoryEntry]:
        """Return recent history entries ordered by newest first."""
        rows = list_query_rows(self._database_path, limit=limit)
        return [row_to_query_entry(row) for row in rows]

    def count_entries(self) -> int:
        """Return the number of persisted grounded ask entries."""
        return count_query_rows(self._database_path)

    def save_agent_runtime_artifact(
        self,
        artifact: AgentRuntimeArtifact,
        *,
        latency_ms: int | None = None,
    ) -> AgentRunHistoryEntry:
        """Persist an agent runtime artifact and return the created history entry."""
        artifact_payload = serialize_agent_runtime_payload(artifact)
        entry_id, created_at = save_agent_runtime_artifact_row(
            self._database_path,
            artifact=artifact,
            artifact_payload=artifact_payload,
            latency_ms=latency_ms,
            retention_limit=self._agent_run_history_retention,
        )

        return AgentRunHistoryEntry(
            entry_id=entry_id,
            created_at=created_at,
            request_text=artifact.request_text,
            normalized_goal=artifact.normalized_goal,
            model=artifact.model,
            task_mode=artifact.task_mode,
            status=artifact.status,
            scope_dirs=tuple(artifact.scope_dirs),
            citations=artifact.citations,
            latency_ms=latency_ms,
            artifact_payload=artifact_payload,
        )

    def list_agent_runs(self, *, limit: int = 20) -> list[AgentRunHistoryEntry]:
        """Return recent persisted agent-runtime artifacts ordered by newest first."""
        rows = list_agent_run_rows(self._database_path, limit=limit)
        return [row_to_agent_run_entry(row) for row in rows]

    def update_agent_runtime_task_plan(
        self,
        *,
        entry_id: int,
        task_plan_payload: dict[str, object],
    ) -> AgentRunHistoryEntry | None:
        """Persist a task-plan update for one saved agent-runtime artifact."""
        updated_row = update_agent_runtime_task_plan_row(
            self._database_path,
            entry_id=entry_id,
            task_plan_payload=task_plan_payload,
        )
        return row_to_agent_run_entry(updated_row) if updated_row is not None else None

    def count_agent_runs(self) -> int:
        """Return the number of persisted agent-runtime artifacts."""
        return count_agent_run_rows(self._database_path)

    def save_benchmark_run_result(self, result) -> BenchmarkRunHistoryEntry:
        """Persist one benchmark run artifact and return the created entry."""
        result_payload = serialize_benchmark_result_payload(result.result_payload)
        entry_id, created_at = save_benchmark_run_result_row(
            self._database_path,
            result=result,
            result_payload=result_payload,
            retention_limit=self._benchmark_history_retention,
        )
        return BenchmarkRunHistoryEntry(
            entry_id=entry_id,
            created_at=created_at,
            pack_id=result.pack_id,
            task_id=result.task_id,
            category=result.category,
            workflow=result.workflow,
            model=result.model,
            status=result.status,
            scope_dirs=tuple(result.scope_dirs),
            prompt_text=result.prompt_text,
            latency_ms=result.latency_ms,
            result_payload=result_payload,
        )

    def list_benchmark_runs(self, *, limit: int = 20) -> list[BenchmarkRunHistoryEntry]:
        """Return recent benchmark run artifacts ordered by newest first."""
        rows = list_benchmark_run_rows(self._database_path, limit=limit)
        return [row_to_benchmark_run_entry(row) for row in rows]

    def count_benchmark_runs(self) -> int:
        """Return the number of persisted benchmark run artifacts."""
        return count_benchmark_run_rows(self._database_path)


__all__ = [
    "DEFAULT_AGENT_RUN_HISTORY_RETENTION",
    "DEFAULT_BENCHMARK_HISTORY_RETENTION",
    "DEFAULT_QUERY_HISTORY_RETENTION",
    "SQLiteQueryHistoryRepository",
]

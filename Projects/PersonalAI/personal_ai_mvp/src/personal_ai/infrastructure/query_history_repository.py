"""SQLite-backed persistence for grounded query history."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from personal_ai.domain.models import (
    AgentRunHistoryEntry,
    AgentRuntimeArtifact,
    BenchmarkRunHistoryEntry,
    GeneratedAnswer,
    QueryHistoryEntry,
)

_DEFAULT_QUERY_HISTORY_RETENTION = 200
_DEFAULT_AGENT_RUN_HISTORY_RETENTION = 120
_DEFAULT_BENCHMARK_HISTORY_RETENTION = 200
_PROMPT_MESSAGE_LIMIT = 8
_PROMPT_MESSAGE_CHAR_LIMIT = 600
_PROMPT_QUESTION_CHAR_LIMIT = 500
_STEP_TEXT_CHAR_LIMIT = 900
_ACTION_TEXT_CHAR_LIMIT = 700
_FINAL_OUTPUT_CHAR_LIMIT = 2200


class SQLiteQueryHistoryRepository:
    """Stores grounded ask interactions in a local SQLite database."""

    def __init__(
        self,
        database_path: Path,
        *,
        query_history_retention: int = _DEFAULT_QUERY_HISTORY_RETENTION,
        agent_run_history_retention: int = _DEFAULT_AGENT_RUN_HISTORY_RETENTION,
        benchmark_history_retention: int = _DEFAULT_BENCHMARK_HISTORY_RETENTION,
    ) -> None:
        self._database_path = database_path
        self._query_history_retention = max(1, query_history_retention)
        self._agent_run_history_retention = max(1, agent_run_history_retention)
        self._benchmark_history_retention = max(1, benchmark_history_retention)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

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
        task_mode = (
            answer.prompt.task_mode
            if answer.prompt is not None
            else "general"
        )
        prompt_payload = _serialize_prompt_payload(answer.prompt)
        created_at = datetime.now(UTC)

        with closing(sqlite3.connect(self._database_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO query_history (
                    created_at,
                    question,
                    answer_text,
                    model,
                    task_mode,
                    scope_dirs_json,
                    citations_json,
                    latency_ms,
                    prompt_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at.isoformat(),
                    answer.question,
                    answer.answer_text,
                    answer.model,
                    task_mode,
                    json.dumps(list(scope_dirs), ensure_ascii=True),
                    json.dumps(list(answer.citations), ensure_ascii=True),
                    latency_ms,
                    json.dumps(prompt_payload, ensure_ascii=True) if prompt_payload is not None else None,
                ),
            )
            self._prune_history_table(
                connection,
                table_name="query_history",
                retention_limit=self._query_history_retention,
            )
            entry_id = int(cursor.lastrowid)
            connection.commit()

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
        effective_limit = max(1, limit)
        with closing(sqlite3.connect(self._database_path)) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    question,
                    answer_text,
                    model,
                    task_mode,
                    scope_dirs_json,
                    citations_json,
                    latency_ms,
                    prompt_json
                FROM query_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (effective_limit,),
            ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def count_entries(self) -> int:
        """Return the number of persisted grounded ask entries."""
        with closing(sqlite3.connect(self._database_path)) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM query_history"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def save_agent_runtime_artifact(
        self,
        artifact: AgentRuntimeArtifact,
        *,
        latency_ms: int | None = None,
    ) -> AgentRunHistoryEntry:
        """Persist an agent runtime artifact and return the created history entry."""
        artifact_payload = _serialize_agent_runtime_payload(artifact)
        created_at = datetime.now(UTC)

        with closing(sqlite3.connect(self._database_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_run_history (
                    created_at,
                    request_text,
                    normalized_goal,
                    model,
                    task_mode,
                    status,
                    scope_dirs_json,
                    citations_json,
                    latency_ms,
                    artifact_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at.isoformat(),
                    artifact.request_text,
                    artifact.normalized_goal,
                    artifact.model,
                    artifact.task_mode,
                    artifact.status,
                    json.dumps(list(artifact.scope_dirs), ensure_ascii=True),
                    json.dumps(list(artifact.citations), ensure_ascii=True),
                    latency_ms,
                    json.dumps(artifact_payload, ensure_ascii=True),
                ),
            )
            self._prune_history_table(
                connection,
                table_name="agent_run_history",
                retention_limit=self._agent_run_history_retention,
            )
            entry_id = int(cursor.lastrowid)
            connection.commit()

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
        effective_limit = max(1, limit)
        with closing(sqlite3.connect(self._database_path)) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    request_text,
                    normalized_goal,
                    model,
                    task_mode,
                    status,
                    scope_dirs_json,
                    citations_json,
                    latency_ms,
                    artifact_json
                FROM agent_run_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (effective_limit,),
            ).fetchall()
        return [_row_to_agent_run_entry(row) for row in rows]

    def update_agent_runtime_task_plan(
        self,
        *,
        entry_id: int,
        task_plan_payload: dict[str, object],
    ) -> AgentRunHistoryEntry | None:
        """Persist a task-plan update for one saved agent-runtime artifact."""
        with closing(sqlite3.connect(self._database_path)) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    request_text,
                    normalized_goal,
                    model,
                    task_mode,
                    status,
                    scope_dirs_json,
                    citations_json,
                    latency_ms,
                    artifact_json
                FROM agent_run_history
                WHERE id = ?
                """,
                (entry_id,),
            ).fetchone()
            if row is None:
                return None

            artifact_payload = json.loads(str(row[10])) if row[10] else {}
            artifact_payload["task_plan"] = task_plan_payload
            connection.execute(
                """
                UPDATE agent_run_history
                SET artifact_json = ?
                WHERE id = ?
                """,
                (
                    json.dumps(artifact_payload, ensure_ascii=True),
                    entry_id,
                ),
            )
            connection.commit()

        updated_row = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            json.dumps(artifact_payload, ensure_ascii=True),
        )
        return _row_to_agent_run_entry(updated_row)

    def count_agent_runs(self) -> int:
        """Return the number of persisted agent-runtime artifacts."""
        with closing(sqlite3.connect(self._database_path)) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM agent_run_history"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def save_benchmark_run_result(self, result) -> BenchmarkRunHistoryEntry:
        """Persist one benchmark run artifact and return the created entry."""
        created_at = datetime.now(UTC)
        with closing(sqlite3.connect(self._database_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO benchmark_run_history (
                    created_at,
                    pack_id,
                    task_id,
                    category,
                    workflow,
                    model,
                    status,
                    scope_dirs_json,
                    prompt_text,
                    latency_ms,
                    result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at.isoformat(),
                    result.pack_id,
                    result.task_id,
                    result.category,
                    result.workflow,
                    result.model,
                    result.status,
                    json.dumps(list(result.scope_dirs), ensure_ascii=True),
                    result.prompt_text,
                    result.latency_ms,
                    json.dumps(result.result_payload, ensure_ascii=True),
                ),
            )
            self._prune_history_table(
                connection,
                table_name="benchmark_run_history",
                retention_limit=self._benchmark_history_retention,
            )
            entry_id = int(cursor.lastrowid)
            connection.commit()
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
            result_payload=result.result_payload,
        )

    def list_benchmark_runs(self, *, limit: int = 20) -> list[BenchmarkRunHistoryEntry]:
        """Return recent benchmark run artifacts ordered by newest first."""
        effective_limit = max(1, limit)
        with closing(sqlite3.connect(self._database_path)) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    pack_id,
                    task_id,
                    category,
                    workflow,
                    model,
                    status,
                    scope_dirs_json,
                    prompt_text,
                    latency_ms,
                    result_json
                FROM benchmark_run_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (effective_limit,),
            ).fetchall()
        return [_row_to_benchmark_run_entry(row) for row in rows]

    def count_benchmark_runs(self) -> int:
        """Return the number of persisted benchmark run artifacts."""
        with closing(sqlite3.connect(self._database_path)) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM benchmark_run_history"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def _ensure_schema(self) -> None:
        with closing(sqlite3.connect(self._database_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    model TEXT NOT NULL,
                    task_mode TEXT NOT NULL,
                    scope_dirs_json TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    latency_ms INTEGER,
                    prompt_json TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    request_text TEXT NOT NULL,
                    normalized_goal TEXT NOT NULL,
                    model TEXT NOT NULL,
                    task_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scope_dirs_json TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    latency_ms INTEGER,
                    artifact_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    pack_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    workflow TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scope_dirs_json TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    latency_ms INTEGER,
                    result_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _prune_history_table(
        self,
        connection: sqlite3.Connection,
        *,
        table_name: str,
        retention_limit: int,
    ) -> None:
        connection.execute(
            f"""
            DELETE FROM {table_name}
            WHERE id NOT IN (
                SELECT id
                FROM {table_name}
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (retention_limit,),
        )


def _row_to_entry(row: tuple[object, ...]) -> QueryHistoryEntry:
    prompt_json = row[9]
    return QueryHistoryEntry(
        entry_id=int(row[0]),
        created_at=datetime.fromisoformat(str(row[1])),
        question=str(row[2]),
        answer_text=str(row[3]),
        model=str(row[4]),
        task_mode=str(row[5]),
        scope_dirs=tuple(json.loads(str(row[6]))),
        citations=tuple(json.loads(str(row[7]))),
        latency_ms=int(row[8]) if row[8] is not None else None,
        prompt_payload=json.loads(str(prompt_json)) if prompt_json else None,
    )


def _row_to_agent_run_entry(row: tuple[object, ...]) -> AgentRunHistoryEntry:
    artifact_json = row[10]
    return AgentRunHistoryEntry(
        entry_id=int(row[0]),
        created_at=datetime.fromisoformat(str(row[1])),
        request_text=str(row[2]),
        normalized_goal=str(row[3]),
        model=str(row[4]),
        task_mode=str(row[5]),
        status=str(row[6]),
        scope_dirs=tuple(json.loads(str(row[7]))),
        citations=tuple(json.loads(str(row[8]))),
        latency_ms=int(row[9]) if row[9] is not None else None,
        artifact_payload=json.loads(str(artifact_json)) if artifact_json else None,
    )


def _row_to_benchmark_run_entry(row: tuple[object, ...]) -> BenchmarkRunHistoryEntry:
    result_json = row[11]
    return BenchmarkRunHistoryEntry(
        entry_id=int(row[0]),
        created_at=datetime.fromisoformat(str(row[1])),
        pack_id=str(row[2]),
        task_id=str(row[3]),
        category=str(row[4]),
        workflow=str(row[5]),
        model=str(row[6]),
        status=str(row[7]),
        scope_dirs=tuple(json.loads(str(row[8]))),
        prompt_text=str(row[9]),
        latency_ms=int(row[10]) if row[10] is not None else None,
        result_payload=json.loads(str(result_json)) if result_json else None,
    )


def _serialize_prompt_payload(prompt) -> dict[str, object] | None:
    if prompt is None:
        return None
    compact_messages = [
        {
            "role": message.role,
            "content": _compact_text(
                message.content,
                limit=_PROMPT_MESSAGE_CHAR_LIMIT,
            ),
        }
        for message in prompt.messages[-_PROMPT_MESSAGE_LIMIT:]
    ]
    return {
        "question": _compact_text(
            prompt.question,
            limit=_PROMPT_QUESTION_CHAR_LIMIT,
        ),
        "task_mode": prompt.task_mode,
        "citations": list(prompt.citations),
        "messages": compact_messages,
        "retrieval": {
            "question": _compact_text(
                prompt.retrieval.question,
                limit=_PROMPT_QUESTION_CHAR_LIMIT,
            ),
            "primary_notes": [
                _serialize_retrieved_note(item)
                for item in prompt.retrieval.primary_notes
            ],
            "related_notes": [
                _serialize_retrieved_note(item)
                for item in prompt.retrieval.related_notes
            ],
        },
    }


def _serialize_retrieved_note(item) -> dict[str, object]:
    return {
        "score": item.score,
        "reason": item.reason,
        "note": _serialize_note_snapshot(item.note),
    }


def _serialize_agent_runtime_payload(artifact: AgentRuntimeArtifact) -> dict[str, object]:
    task_plan = getattr(artifact, "task_plan", None)
    return {
        "generated_at": artifact.generated_at.isoformat(),
        "history_entry_id": getattr(artifact, "history_entry_id", None),
        "model": artifact.model,
        "executor_model": getattr(artifact, "executor_model", None),
        "critic_model": getattr(artifact, "critic_model", None),
        "synthesis_model": getattr(artifact, "synthesis_model", None),
        "discussion_preset": getattr(artifact, "discussion_preset", None),
        "request_text": artifact.request_text,
        "normalized_goal": artifact.normalized_goal,
        "task_mode": artifact.task_mode,
        "status": artifact.status,
        "scope_dirs": list(artifact.scope_dirs),
        "citations": list(artifact.citations),
        "steps": [
            {
                "step_index": step.step_index,
                "kind": step.kind,
                "title": step.title,
                "input_text": _compact_text(
                    step.input_text,
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ),
                "output_text": _compact_text(
                    step.output_text,
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ),
                "observation": _compact_text(
                    step.observation,
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ),
            }
            for step in artifact.steps
        ],
        "recommended_actions": [
            {
                "action_type": action.action_type,
                "title": action.title,
                "target": action.target,
                "instruction": _compact_text(
                    action.instruction,
                    limit=_ACTION_TEXT_CHAR_LIMIT,
                ),
                "rationale": _compact_text(
                    action.rationale,
                    limit=_ACTION_TEXT_CHAR_LIMIT,
                ),
            }
            for action in artifact.recommended_actions
        ],
        "action_executions": [
            {
                "action_type": execution.action_type,
                "target": execution.target,
                "status": execution.status,
                "output_text": _compact_text(
                    execution.output_text,
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ),
            }
            for execution in artifact.action_executions
        ],
        "task_plan": (
            {
                "goal": task_plan.goal,
                "current_focus": task_plan.current_focus,
                "summary": task_plan.summary,
                "entries": [
                    {
                        "step_index": entry.step_index,
                        "title": entry.title,
                        "status": entry.status,
                        "details": entry.details,
                        "source_section": entry.source_section,
                    }
                    for entry in task_plan.entries
                ],
                "validation_checks": list(task_plan.validation_checks),
            }
            if task_plan is not None
            else None
        ),
        "discussion_trace": (
            {
                "preset": artifact.discussion_trace.preset,
                "planner_draft": _compact_text(
                    artifact.discussion_trace.planner_draft,
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ),
                "critic_feedback": _compact_text(
                    artifact.discussion_trace.critic_feedback or "",
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ) if artifact.discussion_trace.critic_feedback else None,
                "synthesis_output": _compact_text(
                    artifact.discussion_trace.synthesis_output or "",
                    limit=_STEP_TEXT_CHAR_LIMIT,
                ) if artifact.discussion_trace.synthesis_output else None,
                "fallback_used": artifact.discussion_trace.fallback_used,
            }
            if getattr(artifact, "discussion_trace", None) is not None
            else None
        ),
        "final_output": _compact_text(
            artifact.final_output,
            limit=_FINAL_OUTPUT_CHAR_LIMIT,
        ),
        "prompt": _serialize_prompt_payload(artifact.prompt),
    }


def _serialize_note_snapshot(note) -> dict[str, object]:
    """Persist a compact note snapshot for audit/history without duplicating the full vault."""
    return {
        "path": note.path.as_posix(),
        "title": note.title,
        "excerpt": _compact_text(note.content, limit=320),
        "content_length": len(note.content),
        "metadata": {"values": dict(note.metadata.values)},
        "links": [
            {
                "raw": link.raw,
                "target": link.target,
                "alias": link.alias,
            }
            for link in note.links
        ],
    }


def _compact_text(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."

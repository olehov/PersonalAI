"""Persistence helpers for agent runtime history."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from domain.models import AgentRuntimeArtifact
from infrastructure.history.repository_support.common import (
    count_table_rows,
    prune_history_table,
)

_AGENT_RUN_SELECT = """
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
"""


def save_agent_runtime_artifact_row(
    database_path: Path,
    *,
    artifact: AgentRuntimeArtifact,
    artifact_payload: dict[str, object],
    latency_ms: int | None,
    retention_limit: int,
) -> tuple[int, datetime]:
    """Persist one agent runtime artifact row and return its id and timestamp."""
    created_at = datetime.now(UTC)
    with closing(sqlite3.connect(database_path)) as connection:
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
        prune_history_table(
            connection,
            table_name="agent_run_history",
            retention_limit=retention_limit,
        )
        entry_id = int(cursor.lastrowid)
        connection.commit()
    return entry_id, created_at


def list_agent_run_rows(database_path: Path, *, limit: int) -> list[tuple[object, ...]]:
    """Load recent agent runtime rows."""
    effective_limit = max(1, limit)
    with closing(sqlite3.connect(database_path)) as connection:
        return connection.execute(
            f"""
            {_AGENT_RUN_SELECT}
            ORDER BY id DESC
            LIMIT ?
            """,
            (effective_limit,),
        ).fetchall()


def update_agent_runtime_task_plan_row(
    database_path: Path,
    *,
    entry_id: int,
    task_plan_payload: dict[str, object],
) -> tuple[object, ...] | None:
    """Update the task plan inside one stored artifact row."""
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            f"""
            {_AGENT_RUN_SELECT}
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

    return (
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


def count_agent_run_rows(database_path: Path) -> int:
    """Count agent runtime history rows."""
    return count_table_rows(database_path, "agent_run_history")

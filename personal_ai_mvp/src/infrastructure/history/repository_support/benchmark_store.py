"""Persistence helpers for benchmark run history."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from infrastructure.history.repository_support.common import (
    count_table_rows,
    prune_history_table,
)


def save_benchmark_run_result_row(
    database_path: Path,
    *,
    result,
    result_payload: dict[str, object],
    retention_limit: int,
) -> tuple[int, datetime]:
    """Persist one benchmark run row and return its id and timestamp."""
    created_at = datetime.now(UTC)
    with closing(sqlite3.connect(database_path)) as connection:
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
                json.dumps(result_payload, ensure_ascii=True),
            ),
        )
        prune_history_table(
            connection,
            table_name="benchmark_run_history",
            retention_limit=retention_limit,
        )
        entry_id = int(cursor.lastrowid)
        connection.commit()
    return entry_id, created_at


def list_benchmark_run_rows(database_path: Path, *, limit: int) -> list[tuple[object, ...]]:
    """Load recent benchmark run rows."""
    effective_limit = max(1, limit)
    with closing(sqlite3.connect(database_path)) as connection:
        return connection.execute(
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


def count_benchmark_run_rows(database_path: Path) -> int:
    """Count benchmark run history rows."""
    return count_table_rows(database_path, "benchmark_run_history")

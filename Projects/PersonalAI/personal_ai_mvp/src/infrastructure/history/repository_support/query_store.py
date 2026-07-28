"""Persistence helpers for grounded answer history."""

from __future__ import annotations

from contextlib import closing
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3

from domain.models import GeneratedAnswer
from infrastructure.history.repository_support.common import (
    count_table_rows,
    prune_history_table,
)


def save_generated_answer_row(
    database_path: Path,
    *,
    answer: GeneratedAnswer,
    task_mode: str,
    prompt_payload: dict[str, object] | None,
    scope_dirs: tuple[str, ...],
    latency_ms: int | None,
    retention_limit: int,
) -> tuple[int, datetime]:
    """Persist one grounded answer row and return its id and timestamp."""
    created_at = datetime.now(UTC)
    with closing(sqlite3.connect(database_path)) as connection:
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
        prune_history_table(
            connection,
            table_name="query_history",
            retention_limit=retention_limit,
        )
        entry_id = int(cursor.lastrowid)
        connection.commit()
    return entry_id, created_at


def list_query_rows(database_path: Path, *, limit: int) -> list[tuple[object, ...]]:
    """Load recent grounded answer rows."""
    effective_limit = max(1, limit)
    with closing(sqlite3.connect(database_path)) as connection:
        return connection.execute(
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


def count_query_rows(database_path: Path) -> int:
    """Count grounded answer history rows."""
    return count_table_rows(database_path, "query_history")

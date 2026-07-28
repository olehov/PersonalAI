"""Shared SQLite helpers for history persistence."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3


def count_table_rows(database_path: Path, table_name: str) -> int:
    """Count rows in one history table."""
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0]) if row is not None else 0


def prune_history_table(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    retention_limit: int,
) -> None:
    """Prune one history table down to the configured retention."""
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

"""Schema management for persisted history tables."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3


def ensure_history_schema(database_path: Path) -> None:
    """Create the SQLite history tables when missing."""
    with closing(sqlite3.connect(database_path)) as connection:
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

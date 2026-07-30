"""Row-to-domain mapping helpers for SQLite history persistence."""

from __future__ import annotations

from datetime import datetime
import json

from domain.models import (
    AgentRunHistoryEntry,
    BenchmarkRunHistoryEntry,
    QueryHistoryEntry,
)


def row_to_query_entry(row: tuple[object, ...]) -> QueryHistoryEntry:
    """Build one grounded-answer history entry from a SQLite row."""
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


def row_to_agent_run_entry(row: tuple[object, ...]) -> AgentRunHistoryEntry:
    """Build one agent-run history entry from a SQLite row."""
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


def row_to_benchmark_run_entry(row: tuple[object, ...]) -> BenchmarkRunHistoryEntry:
    """Build one benchmark-run history entry from a SQLite row."""
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

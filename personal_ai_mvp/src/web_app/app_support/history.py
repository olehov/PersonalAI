"""History and health helpers for the PersonalAI web application."""

from __future__ import annotations

from application.shared.serializers import (
    serialize_agent_run_history_entry,
    serialize_benchmark_run_history_entry,
    serialize_query_history_entry,
)


def list_ask_history(repository, *, limit: int) -> list[dict[str, object]]:
    return [
        serialize_query_history_entry(entry)
        for entry in repository.list_entries(limit=limit)
    ]


def list_agent_history(repository, *, limit: int) -> list[dict[str, object]]:
    return [
        serialize_agent_run_history_entry(entry)
        for entry in repository.list_agent_runs(limit=limit)
    ]


def list_benchmark_history(repository, *, limit: int) -> list[dict[str, object]]:
    return [
        serialize_benchmark_run_history_entry(entry)
        for entry in repository.list_benchmark_runs(limit=limit)
    ]


def history_overview(repository) -> dict[str, int]:
    return {
        "ask": repository.count_entries(),
        "agent": repository.count_agent_runs(),
        "benchmark": repository.count_benchmark_runs(),
    }


def health_status(*, knowledge, has_frontend_assets: bool, web_search) -> dict[str, object]:
    snapshot = web_search.refresh_health()
    return {
        "status": "ok",
        "vault_loaded": True,
        "note_count": knowledge.scan_summary()["note_count"],
        "frontend_assets": has_frontend_assets,
        "web_search": {
            "provider": snapshot.provider,
            "enabled": snapshot.enabled,
            "status": snapshot.status,
            "degraded": snapshot.degraded,
            "last_error": snapshot.last_error,
            "last_attempted_at": snapshot.last_attempted_at,
            "last_success_at": snapshot.last_success_at,
        },
    }

"""CLI renderers for benchmark packs, runs, and history."""

from __future__ import annotations

import json

from application.benchmark.pack_service import BenchmarkPackService
from application.shared.serializers import serialize_benchmark_run_history_entry


def render_benchmark_pack(
    pack,
    output_format: str,
    *,
    task_id: str | None,
    category: str | None = None,
) -> str:
    payload = BenchmarkPackService().serialize_pack(pack)
    if task_id:
        payload["tasks"] = [
            task for task in payload["tasks"] if task["task_id"] == task_id
        ]
    if category:
        payload["tasks"] = [
            task for task in payload["tasks"] if task["category"] == category
        ]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"title: {payload['title']}",
        f"description: {payload['description']}",
        f"task_count: {len(payload['tasks'])}",
    ]
    if category:
        lines.append(f"category_filter: {category}")
    lines.append("tasks:")
    for task in payload["tasks"]:
        lines.append(
            f"- {task['task_id']} | {task['category']} | {task['workflow']} | {task['title']}"
        )
        lines.append(f"  objective: {task['objective']}")
        if task["scope_dirs"]:
            lines.append(f"  scope_dirs: {', '.join(task['scope_dirs'])}")
    return "\n".join(lines)


def render_benchmark_run_result(result, output_format: str) -> str:
    payload = {
        "pack_id": result.pack_id,
        "task_id": result.task_id,
        "category": result.category,
        "workflow": result.workflow,
        "model": result.model,
        "status": result.status,
        "scope_dirs": list(result.scope_dirs),
        "prompt_text": result.prompt_text,
        "latency_ms": result.latency_ms,
        "result_payload": result.result_payload,
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"task_id: {payload['task_id']}",
        f"category: {payload['category']}",
        f"workflow: {payload['workflow']}",
        f"model: {payload['model']}",
        f"status: {payload['status']}",
        f"latency_ms: {payload['latency_ms']}",
        "prompt:",
        payload["prompt_text"],
    ]
    result_payload = payload["result_payload"]
    if isinstance(result_payload, dict):
        lines.append("result_keys:")
        for key in result_payload.keys():
            lines.append(f"- {key}")
        turn_results = result_payload.get("turn_results")
        if isinstance(turn_results, list) and turn_results:
            lines.append("turn_results:")
            for turn in turn_results:
                if not isinstance(turn, dict):
                    continue
                turn_index = turn.get("turn_index", "?")
                turn_status = turn.get("status", "unknown")
                turn_prompt = str(turn.get("prompt", "")).strip().splitlines()[0]
                lines.append(f"- turn {turn_index} | {turn_status} | {turn_prompt}")
    return "\n".join(lines)


def render_benchmark_history(entries, output_format: str) -> str:
    payload = [serialize_benchmark_run_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved benchmark run history."

    lines: list[str] = []
    for entry in payload:
        result_payload = entry.get("result_payload") if isinstance(entry, dict) else None
        turn_count = 0
        if isinstance(result_payload, dict):
            turn_results = result_payload.get("turn_results")
            if isinstance(turn_results, list):
                turn_count = len(turn_results)
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['pack_id']} | "
            f"{entry['task_id']} | {entry['workflow']} | {entry['model']} | {entry['status']} | "
            f"turns={turn_count}"
        )
    return "\n".join(lines)


def render_benchmark_compare_result(comparison, output_format: str) -> str:
    payload = {
        "pack_id": comparison.pack_id,
        "task_ids": list(comparison.task_ids),
        "entries": [
            {
                "model": entry.model,
                "task_id": entry.task_id,
                "workflow": entry.workflow,
                "status": entry.status,
                "latency_ms": entry.latency_ms,
                "result_payload": entry.result_payload,
            }
            for entry in comparison.entries
        ],
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"task_count: {len(payload['task_ids'])}",
        f"entry_count: {len(payload['entries'])}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['task_id']} | {entry['model']} | {entry['workflow']} | "
            f"{entry['status']} | {entry['latency_ms']} ms"
        )
    return "\n".join(lines)

"""CLI renderers for agent runtime artifacts and history."""

from __future__ import annotations

import json

from application.shared.serializers import (
    serialize_agent_run_history_entry,
    serialize_agent_runtime_artifact,
)


def render_agent_runtime_artifact(artifact, output_format: str) -> str:
    payload = serialize_agent_runtime_artifact(artifact)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    overview = payload.get("overview", {})
    lines = [
        f"model: {payload['model']}",
        f"status: {payload['status']}",
        f"task_mode: {payload['task_mode']}",
        f"normalized_goal: {payload['normalized_goal']}",
        f"scope_dirs: {', '.join(payload['scope_dirs']) if payload['scope_dirs'] else 'none'}",
        (
            "overview: "
            f"steps={overview.get('step_count', 0)} | "
            f"recommended_actions={overview.get('recommended_action_count', 0)} | "
            f"executed={overview.get('executed_action_count', 0)} | "
            f"deferred={overview.get('deferred_action_count', 0)} | "
            f"failed={overview.get('failed_action_count', 0)} | "
            f"citations={overview.get('citation_count', 0)}"
        ),
        "timeline:",
    ]
    for step in payload["steps"]:
        lines.append(f"- {step['step_index']}. {step['kind']} | {step['title']}")
        lines.append(f"  observation: {step['observation']}")
    if payload["recommended_actions"]:
        lines.append("recommended_actions:")
        for action in payload["recommended_actions"]:
            lines.append(
                f"- {action['action_type']} | {action['title']} | {action['target']}"
            )
            lines.append(f"  instruction: {action['instruction']}")
    if payload["action_executions"]:
        lines.append("action_executions:")
        for execution in payload["action_executions"]:
            lines.append(
                f"- {execution['action_type']} | {execution['status']} | {execution['target']}"
            )
    lines.extend(["final_output:", payload["final_output"]])
    if payload["citations"]:
        lines.append("citations:")
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    return "\n".join(lines)


def render_agent_history(entries, output_format: str) -> str:
    payload = [serialize_agent_run_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved agent runtime history."

    lines: list[str] = []
    for entry in payload:
        overview = (
            entry["artifact_payload"].get("overview", {})
            if isinstance(entry.get("artifact_payload"), dict)
            else {}
        )
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['model']} | "
            f"{entry['task_mode']} | {entry['status']} | "
            f"steps={overview.get('step_count', 0)} | "
            f"actions={overview.get('recommended_action_count', 0)} | "
            f"{entry['request_text']}"
        )
    return "\n".join(lines)

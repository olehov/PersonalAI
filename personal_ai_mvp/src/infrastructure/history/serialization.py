"""Payload compaction helpers for persisted query history."""

from __future__ import annotations

from domain.models import AgentRuntimeArtifact

PROMPT_MESSAGE_LIMIT = 8
PROMPT_MESSAGE_CHAR_LIMIT = 600
PROMPT_QUESTION_CHAR_LIMIT = 500
STEP_TEXT_CHAR_LIMIT = 900
ACTION_TEXT_CHAR_LIMIT = 700
FINAL_OUTPUT_CHAR_LIMIT = 2200
BENCHMARK_PROMPT_CHAR_LIMIT = 700


def serialize_prompt_payload(prompt) -> dict[str, object] | None:
    """Persist a compact prompt payload without duplicating the full context."""
    if prompt is None:
        return None
    compact_messages = [
        {
            "role": message.role,
            "content": compact_text(
                message.content,
                limit=PROMPT_MESSAGE_CHAR_LIMIT,
            ),
        }
        for message in prompt.messages[-PROMPT_MESSAGE_LIMIT:]
    ]
    return {
        "question": compact_text(
            prompt.question,
            limit=PROMPT_QUESTION_CHAR_LIMIT,
        ),
        "task_mode": prompt.task_mode,
        "citations": list(prompt.citations),
        "messages": compact_messages,
        "retrieval": {
            "question": compact_text(
                prompt.retrieval.question,
                limit=PROMPT_QUESTION_CHAR_LIMIT,
            ),
            "primary_notes": [
                serialize_retrieved_note(item)
                for item in prompt.retrieval.primary_notes
            ],
            "related_notes": [
                serialize_retrieved_note(item)
                for item in prompt.retrieval.related_notes
            ],
        },
    }


def serialize_retrieved_note(item) -> dict[str, object]:
    """Persist one compact retrieved-note record."""
    return {
        "score": item.score,
        "reason": item.reason,
        "note": serialize_note_snapshot(item.note),
    }


def serialize_agent_runtime_payload(artifact: AgentRuntimeArtifact) -> dict[str, object]:
    """Persist one compact agent-runtime artifact payload."""
    task_plan = getattr(artifact, "task_plan", None)
    return {
        "generated_at": artifact.generated_at.isoformat(),
        "history_entry_id": getattr(artifact, "history_entry_id", None),
        "model": artifact.model,
        "executor_model": getattr(artifact, "executor_model", None),
        "critic_model": getattr(artifact, "critic_model", None),
        "synthesis_model": getattr(artifact, "synthesis_model", None),
        "approver_model": getattr(artifact, "approver_model", None),
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
                "input_text": compact_text(
                    step.input_text,
                    limit=STEP_TEXT_CHAR_LIMIT,
                ),
                "output_text": compact_text(
                    step.output_text,
                    limit=STEP_TEXT_CHAR_LIMIT,
                ),
                "observation": compact_text(
                    step.observation,
                    limit=STEP_TEXT_CHAR_LIMIT,
                ),
            }
            for step in artifact.steps
        ],
        "recommended_actions": [
            {
                "action_type": action.action_type,
                "title": action.title,
                "target": action.target,
                "instruction": compact_text(
                    action.instruction,
                    limit=ACTION_TEXT_CHAR_LIMIT,
                ),
                "rationale": compact_text(
                    action.rationale,
                    limit=ACTION_TEXT_CHAR_LIMIT,
                ),
            }
            for action in artifact.recommended_actions
        ],
        "action_executions": [
            {
                "action_type": execution.action_type,
                "target": execution.target,
                "status": execution.status,
                "output_text": compact_text(
                    execution.output_text,
                    limit=STEP_TEXT_CHAR_LIMIT,
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
                "planner_draft": compact_text(
                    artifact.discussion_trace.planner_draft,
                    limit=STEP_TEXT_CHAR_LIMIT,
                ),
                "critic_feedback": compact_text(
                    artifact.discussion_trace.critic_feedback or "",
                    limit=STEP_TEXT_CHAR_LIMIT,
                ) if artifact.discussion_trace.critic_feedback else None,
                "synthesis_output": compact_text(
                    artifact.discussion_trace.synthesis_output or "",
                    limit=STEP_TEXT_CHAR_LIMIT,
                ) if artifact.discussion_trace.synthesis_output else None,
                "approver_feedback": compact_text(
                    artifact.discussion_trace.approver_feedback or "",
                    limit=STEP_TEXT_CHAR_LIMIT,
                ) if artifact.discussion_trace.approver_feedback else None,
                "approval_status": artifact.discussion_trace.approval_status,
                "planner_revisions": artifact.discussion_trace.planner_revisions,
                "planner_rollbacks": artifact.discussion_trace.planner_rollbacks,
                "fallback_used": artifact.discussion_trace.fallback_used,
            }
            if getattr(artifact, "discussion_trace", None) is not None
            else None
        ),
        "final_output": compact_text(
            artifact.final_output,
            limit=FINAL_OUTPUT_CHAR_LIMIT,
        ),
        "prompt": serialize_prompt_payload(artifact.prompt),
    }


def serialize_note_snapshot(note) -> dict[str, object]:
    """Persist a compact note snapshot for audit/history without duplicating the full vault."""
    return {
        "path": note.path.as_posix(),
        "title": note.title,
        "excerpt": compact_text(note.content, limit=320),
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


def serialize_benchmark_result_payload(payload: dict[str, object] | None) -> dict[str, object] | None:
    """Persist one compact benchmark result payload."""
    if payload is None:
        return None

    compact_payload = {
        key: value
        for key, value in payload.items()
        if key != "turn_results"
    }
    if "final_payload" in compact_payload and isinstance(compact_payload["final_payload"], dict):
        compact_payload["final_payload"] = compact_benchmark_result_leaf(compact_payload["final_payload"])

    turn_results = payload.get("turn_results")
    if isinstance(turn_results, list):
        compact_payload["turn_results"] = [
            serialize_benchmark_turn_result(turn)
            for turn in turn_results
            if isinstance(turn, dict)
        ]
    return compact_payload


def serialize_benchmark_turn_result(turn: dict[str, object]) -> dict[str, object]:
    """Persist one compact benchmark turn result."""
    compact_turn = {
        "turn_index": turn.get("turn_index"),
        "prompt": compact_text(str(turn.get("prompt", "")), limit=BENCHMARK_PROMPT_CHAR_LIMIT),
        "expected_signals": list(turn.get("expected_signals", [])),
        "anti_signals": list(turn.get("anti_signals", [])),
        "notes": list(turn.get("notes", [])),
        "status": turn.get("status"),
    }
    if isinstance(turn.get("result_payload"), dict):
        compact_turn["result_payload"] = compact_benchmark_result_leaf(turn["result_payload"])
    else:
        compact_turn["result_payload"] = turn.get("result_payload")
    return compact_turn


def compact_benchmark_result_leaf(payload: dict[str, object]) -> dict[str, object]:
    """Compact verbose leaf fields inside benchmark result payloads."""
    compact_payload = dict(payload)
    answer_text = compact_payload.get("answer_text")
    if isinstance(answer_text, str):
        compact_payload["answer_text"] = compact_text(answer_text, limit=FINAL_OUTPUT_CHAR_LIMIT)

    final_output = compact_payload.get("final_output")
    if isinstance(final_output, str):
        compact_payload["final_output"] = compact_text(final_output, limit=FINAL_OUTPUT_CHAR_LIMIT)
    return compact_payload


def compact_text(text: str, *, limit: int) -> str:
    """Normalize whitespace and truncate to a fixed storage budget."""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."

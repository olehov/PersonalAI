"""Core knowledge and history serializers."""

from __future__ import annotations

from dataclasses import asdict

from domain.models import (
    AgentRunHistoryEntry,
    BenchmarkRunHistoryEntry,
    DirectoryAnalysisNodeStat,
    DirectoryAnalysisReport,
    DirectoryCoverageSuggestion,
    GeneratedAnswer,
    NoteDocument,
    QueryHistoryEntry,
    RetrievalBundle,
    RetrievedNote,
    AnswerBundle,
)


def serialize_note(note: NoteDocument) -> dict[str, object]:
    """Converts a note to a JSON-friendly dictionary."""
    if hasattr(note, "__dataclass_fields__"):
        payload = asdict(note)
        payload["path"] = note.path.as_posix()
        return payload

    metadata = getattr(getattr(note, "metadata", None), "values", {})
    links = [
        {
            "raw": getattr(link, "raw", ""),
            "target": getattr(link, "target", ""),
            "alias": getattr(link, "alias", None),
        }
        for link in getattr(note, "links", ())
    ]
    return {
        "path": note.path.as_posix(),
        "title": getattr(note, "title", ""),
        "content": getattr(note, "content", ""),
        "metadata": {"values": metadata},
        "links": links,
    }


def serialize_retrieved_note(item: RetrievedNote) -> dict[str, object]:
    """Converts a retrieved note to a JSON-friendly dictionary."""
    return {
        "score": item.score,
        "reason": item.reason,
        "debug_signals": item.debug_signals,
        "selection_summary": _serialize_selection_summary(item.debug_signals),
        "note": serialize_note(item.note),
    }


def _serialize_selection_summary(debug_signals: dict[str, object]) -> dict[str, object]:
    summary = debug_signals.get("selection_summary")
    if isinstance(summary, dict):
        return summary

    return {
        "stage": debug_signals.get("selection_stage", "unknown"),
        "order": debug_signals.get("selection_order"),
        "rank_position": debug_signals.get("rank_position"),
        "selection_reasons": list(debug_signals.get("reason_tags", [])),
    }


def serialize_retrieval_bundle(bundle: RetrievalBundle) -> dict[str, object]:
    """Converts a retrieval bundle to a JSON-friendly dictionary."""
    return {
        "question": bundle.question,
        "primary_notes": [serialize_retrieved_note(item) for item in bundle.primary_notes],
        "related_notes": [serialize_retrieved_note(item) for item in bundle.related_notes],
    }


def serialize_answer_bundle(bundle: AnswerBundle) -> dict[str, object]:
    """Converts an answer bundle to a JSON-friendly dictionary."""
    return {
        "question": bundle.question,
        "task_mode": bundle.task_mode,
        "citations": list(bundle.citations),
        "retrieval": serialize_retrieval_bundle(bundle.retrieval),
        "messages": [
            {"role": message.role, "content": message.content}
            for message in bundle.messages
        ],
    }


def serialize_directory_analysis_node_stat(item: DirectoryAnalysisNodeStat) -> dict[str, object]:
    """Converts a directory graph node stat to a JSON-friendly dictionary."""
    return {
        "note": serialize_note(item.note),
        "inbound_links": item.inbound_links,
        "outbound_links": item.outbound_links,
    }


def serialize_directory_coverage_suggestion(
    suggestion: DirectoryCoverageSuggestion,
) -> dict[str, object]:
    """Converts a directory coverage suggestion to a JSON-friendly dictionary."""
    return {
        "title": suggestion.title,
        "reason": suggestion.reason,
        "source": suggestion.source,
    }


def serialize_directory_analysis_report(report: DirectoryAnalysisReport) -> dict[str, object]:
    """Converts a directory analysis report to a JSON-friendly dictionary."""
    return {
        "directory": report.directory.as_posix(),
        "note_count": report.note_count,
        "notes": [serialize_note(note) for note in report.notes],
        "total_links": report.total_links,
        "internal_link_count": report.internal_link_count,
        "cross_directory_link_count": report.cross_directory_link_count,
        "unresolved_links": list(report.unresolved_links),
        "isolated_notes": [path.as_posix() for path in report.isolated_notes],
        "hub_notes": [serialize_directory_analysis_node_stat(item) for item in report.hub_notes],
        "suggestions": [
            serialize_directory_coverage_suggestion(suggestion)
            for suggestion in report.suggestions
        ],
    }


def serialize_generated_answer(answer: GeneratedAnswer) -> dict[str, object]:
    """Converts a generated answer to a JSON-friendly dictionary."""
    return {
        "model": answer.model,
        "question": answer.question,
        "answer_text": answer.answer_text,
        "citations": list(answer.citations),
        "prompt": serialize_answer_bundle(answer.prompt) if answer.prompt is not None else None,
    }


def serialize_agent_run_history_entry(entry: AgentRunHistoryEntry) -> dict[str, object]:
    """Converts an agent run history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "request_text": entry.request_text,
        "normalized_goal": entry.normalized_goal,
        "model": entry.model,
        "task_mode": entry.task_mode,
        "status": entry.status,
        "scope_dirs": list(entry.scope_dirs),
        "citations": list(entry.citations),
        "latency_ms": entry.latency_ms,
        "artifact_payload": entry.artifact_payload,
    }


def serialize_query_history_entry(entry: QueryHistoryEntry) -> dict[str, object]:
    """Converts a query history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "question": entry.question,
        "answer_text": entry.answer_text,
        "model": entry.model,
        "task_mode": entry.task_mode,
        "scope_dirs": list(entry.scope_dirs),
        "citations": list(entry.citations),
        "latency_ms": entry.latency_ms,
        "prompt_payload": entry.prompt_payload,
    }


def serialize_benchmark_run_history_entry(entry: BenchmarkRunHistoryEntry) -> dict[str, object]:
    """Converts a benchmark run history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "pack_id": entry.pack_id,
        "task_id": entry.task_id,
        "category": entry.category,
        "workflow": entry.workflow,
        "model": entry.model,
        "status": entry.status,
        "scope_dirs": list(entry.scope_dirs),
        "prompt_text": entry.prompt_text,
        "latency_ms": entry.latency_ms,
        "result_payload": entry.result_payload,
    }

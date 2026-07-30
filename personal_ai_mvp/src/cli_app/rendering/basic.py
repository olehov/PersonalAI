"""Core CLI renderers for scan, notes, retrieval, and answers."""

from __future__ import annotations

import json

from application.shared.serializers import (
    serialize_answer_bundle,
    serialize_directory_analysis_report,
    serialize_generated_answer,
    serialize_note,
    serialize_query_history_entry,
    serialize_retrieval_bundle,
)


def render_scan(summary: dict[str, int], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(summary, indent=2)
    return "\n".join(f"{key}: {value}" for key, value in summary.items())


def render_note_list(notes: list, output_format: str) -> str:
    if not notes:
        return "[]" if output_format == "json" else "No notes found."

    if output_format == "json":
        return json.dumps([serialize_note(note) for note in notes], indent=2)

    return "\n".join(f"{note.path.as_posix()} | {note.title}" for note in notes)


def render_note_detail(note, output_format: str) -> str:
    payload = serialize_note(note)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"path: {payload['path']}",
        f"title: {payload['title']}",
        f"metadata: {payload['metadata']['values']}",
        f"links: {len(payload['links'])}",
    ]
    return "\n".join(lines)


def render_retrieval_bundle(bundle, output_format: str) -> str:
    payload = serialize_retrieval_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"question: {payload['question']}", "primary_notes:"]
    if payload["primary_notes"]:
        for item in payload["primary_notes"]:
            lines.append(
                f"- {item['note']['path']} | score={item['score']} | reason={item['reason']}"
            )
    else:
        lines.append("- none")

    lines.append("related_notes:")
    if payload["related_notes"]:
        for item in payload["related_notes"]:
            lines.append(
                f"- {item['note']['path']} | score={item['score']} | reason={item['reason']}"
            )
    else:
        lines.append("- none")

    return "\n".join(lines)


def render_answer_bundle(bundle, output_format: str) -> str:
    payload = serialize_answer_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"question: {payload['question']}", "citations:"]
    if payload["citations"]:
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    else:
        lines.append("- none")

    lines.append("messages:")
    for message in payload["messages"]:
        preview = message["content"].splitlines()[0] if message["content"] else ""
        lines.append(f"- {message['role']}: {preview}")
    return "\n".join(lines)


def render_directory_analysis_report(report, output_format: str) -> str:
    payload = serialize_directory_analysis_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"directory: {payload['directory']}",
        f"note_count: {payload['note_count']}",
        f"total_links: {payload['total_links']}",
        f"internal_link_count: {payload['internal_link_count']}",
        f"cross_directory_link_count: {payload['cross_directory_link_count']}",
        "notes:",
    ]
    if payload["notes"]:
        for note in payload["notes"]:
            lines.append(f"- {note['path']} | {note['title']}")
    else:
        lines.append("- none")

    lines.append("hub_notes:")
    if payload["hub_notes"]:
        for item in payload["hub_notes"]:
            lines.append(
                "- "
                f"{item['note']['path']} | inbound={item['inbound_links']} | "
                f"outbound={item['outbound_links']}"
            )
    else:
        lines.append("- none")

    lines.append("isolated_notes:")
    if payload["isolated_notes"]:
        for path in payload["isolated_notes"]:
            lines.append(f"- {path}")
    else:
        lines.append("- none")

    lines.append("unresolved_links:")
    if payload["unresolved_links"]:
        for target in payload["unresolved_links"]:
            lines.append(f"- {target}")
    else:
        lines.append("- none")

    lines.append("suggestions:")
    if payload["suggestions"]:
        for suggestion in payload["suggestions"]:
            lines.append(
                f"- {suggestion['title']} | {suggestion['source']} | {suggestion['reason']}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines)


def render_generated_answer(answer, output_format: str) -> str:
    payload = serialize_generated_answer(answer)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"model: {payload['model']}", f"question: {payload['question']}", "answer:"]
    lines.append(payload["answer_text"])
    lines.append("citations:")
    if payload["citations"]:
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def render_query_history(entries, output_format: str) -> str:
    payload = [serialize_query_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved query history."

    lines: list[str] = []
    for entry in payload:
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['model']} | "
            f"{entry['task_mode']} | {entry['question']}"
        )
    return "\n".join(lines)

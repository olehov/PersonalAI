"""CLI renderers for note proposals, drafts, and maintenance flows."""

from __future__ import annotations

import json

from application.shared.serializers import (
    serialize_applied_note_change,
    serialize_generated_note_draft,
    serialize_maintenance_draft_plan,
    serialize_maintenance_plan,
    serialize_maintenance_report,
    serialize_note_change_proposal,
)


def render_note_change_proposal(proposal, output_format: str) -> str:
    payload = serialize_note_change_proposal(proposal)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"action: {payload['action']}",
        f"target_path: {payload['target_path']}",
        f"title: {payload['title']}",
        f"reason: {payload['reason']}",
    ]
    if payload["similar_notes"]:
        lines.append("similar_notes:")
        for note in payload["similar_notes"]:
            lines.append(f"- {note}")
    if payload["warnings"]:
        lines.append("warnings:")
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def render_applied_note_change(proposal, change, output_format: str) -> str:
    payload = {
        "proposal": serialize_note_change_proposal(proposal),
        "change": serialize_applied_note_change(change),
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"action: {payload['change']['action']}",
        f"target_path: {payload['change']['target_path']}",
        f"backup_path: {payload['change']['backup_path']}",
        f"archive_path: {payload['change']['archive_path']}",
    ]
    return "\n".join(lines)


def render_generated_note_draft(draft, output_format: str) -> str:
    payload = serialize_generated_note_draft(draft)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"model: {payload['model']}",
        f"title: {payload['title']}",
        f"action: {payload['proposal']['action']}",
        f"target_path: {payload['proposal']['target_path']}",
        "content:",
        payload["content"],
    ]
    if payload["proposal"]["warnings"]:
        lines.append("warnings:")
        for warning in payload["proposal"]["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def render_generated_note_application(draft, applied, output_format: str) -> str:
    payload = {
        "draft": serialize_generated_note_draft(draft),
        "change": serialize_applied_note_change(applied),
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"model: {payload['draft']['model']}",
        f"title: {payload['draft']['title']}",
        f"target_path: {payload['change']['target_path']}",
        f"backup_path: {payload['change']['backup_path']}",
    ]
    return "\n".join(lines)


def render_maintenance_report(report, output_format: str) -> str:
    payload = serialize_maintenance_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    findings = payload["findings"]
    if not findings:
        return "No maintenance findings."

    lines = [f"generated_at: {payload['generated_at']}", "findings:"]
    for finding in findings:
        lines.append(
            f"- {finding['kind']} | {finding['note']['path']} | {finding['summary']}"
        )
        if finding["proposal"] is not None:
            lines.append(
                f"  proposal: {finding['proposal']['action']} -> {finding['proposal']['target_path']}"
            )
    return "\n".join(lines)


def render_maintenance_plan(plan, output_format: str) -> str:
    payload = serialize_maintenance_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    entries = payload["entries"]
    if not entries:
        return "No actionable maintenance plan entries."

    lines = [f"generated_at: {payload['generated_at']}", "entries:"]
    for entry in entries:
        finding = entry["finding"]
        proposal = entry["proposal"]
        lines.append(
            f"- {finding['note']['path']} | {finding['kind']} | {proposal['action']} -> {proposal['target_path']}"
        )
        if entry["merged_kinds"]:
            lines.append(f"  merged_kinds: {', '.join(entry['merged_kinds'])}")
    if payload["skipped_paths"]:
        lines.append("skipped_paths:")
        for path in payload["skipped_paths"]:
            lines.append(f"- {path}")
    return "\n".join(lines)


def render_maintenance_draft_plan(plan, output_format: str) -> str:
    payload = serialize_maintenance_draft_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    entries = payload["entries"]
    if not entries:
        return "No maintenance draft plan entries."

    lines = [f"generated_at: {payload['generated_at']}", "entries:"]
    for entry in entries:
        finding = entry["plan_entry"]["finding"]
        proposal = entry["draft"]["proposal"]
        lines.append(
            f"- {finding['note']['path']} | {finding['kind']} | draft -> {proposal['target_path']}"
        )
        companion = entry["draft"].get("companion_proposals", [])
        if companion:
            lines.append(f"  companion_proposals: {len(companion)}")
    return "\n".join(lines)

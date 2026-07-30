"""Note drafting and maintenance serializers."""

from __future__ import annotations

from application.shared.serializer_parts.core import (
    serialize_answer_bundle,
    serialize_note,
)
from domain.models import (
    AppliedNoteChange,
    GeneratedNoteDraft,
    KnowledgeMaintenanceFinding,
    KnowledgeMaintenancePlan,
    KnowledgeMaintenancePlanEntry,
    KnowledgeMaintenanceReport,
    MaintenanceDraftPlan,
    MaintenanceDraftPlanEntry,
    NoteChangeProposal,
)


def serialize_note_change_proposal(proposal: NoteChangeProposal) -> dict[str, object]:
    return {
        "action": proposal.action,
        "target_path": proposal.target_path.as_posix(),
        "title": proposal.title,
        "reason": proposal.reason,
        "proposed_content": proposal.proposed_content,
        "current_content": proposal.current_content,
        "archive_path": proposal.archive_path.as_posix() if proposal.archive_path else None,
        "similar_notes": list(proposal.similar_notes),
        "warnings": list(proposal.warnings),
        "created_at": proposal.created_at.isoformat(),
    }


def serialize_applied_note_change(change: AppliedNoteChange) -> dict[str, object]:
    return {
        "action": change.action,
        "target_path": change.target_path.as_posix(),
        "backup_path": change.backup_path.as_posix() if change.backup_path else None,
        "archive_path": change.archive_path.as_posix() if change.archive_path else None,
        "applied_at": change.applied_at.isoformat(),
    }


def serialize_generated_note_draft(draft: GeneratedNoteDraft) -> dict[str, object]:
    companion_proposals = getattr(draft, "companion_proposals", ())
    return {
        "model": draft.model,
        "title": draft.title,
        "instruction": draft.instruction,
        "content": draft.content,
        "citations": list(draft.citations),
        "proposal": serialize_note_change_proposal(draft.proposal),
        "companion_proposals": [
            serialize_note_change_proposal(proposal)
            for proposal in companion_proposals
        ],
        "prompt": serialize_answer_bundle(draft.prompt) if draft.prompt is not None else None,
    }


def serialize_maintenance_finding(finding: KnowledgeMaintenanceFinding) -> dict[str, object]:
    return {
        "kind": finding.kind,
        "summary": finding.summary,
        "details": list(finding.details),
        "note": serialize_note(finding.note),
        "proposal": (
            serialize_note_change_proposal(finding.proposal)
            if finding.proposal is not None
            else None
        ),
    }


def serialize_maintenance_report(report: KnowledgeMaintenanceReport) -> dict[str, object]:
    return {
        "generated_at": report.generated_at.isoformat(),
        "findings": [serialize_maintenance_finding(finding) for finding in report.findings],
    }


def serialize_maintenance_plan_entry(entry: KnowledgeMaintenancePlanEntry) -> dict[str, object]:
    return {
        "finding": serialize_maintenance_finding(entry.finding),
        "proposal": serialize_note_change_proposal(entry.proposal),
        "merged_kinds": list(entry.merged_kinds),
    }


def serialize_maintenance_plan(plan: KnowledgeMaintenancePlan) -> dict[str, object]:
    return {
        "generated_at": plan.generated_at.isoformat(),
        "entries": [serialize_maintenance_plan_entry(entry) for entry in plan.entries],
        "skipped_paths": list(plan.skipped_paths),
    }


def serialize_maintenance_draft_plan_entry(entry: MaintenanceDraftPlanEntry) -> dict[str, object]:
    return {
        "plan_entry": serialize_maintenance_plan_entry(entry.plan_entry),
        "draft": serialize_generated_note_draft(entry.draft),
    }


def serialize_maintenance_draft_plan(plan: MaintenanceDraftPlan) -> dict[str, object]:
    return {
        "generated_at": plan.generated_at.isoformat(),
        "entries": [serialize_maintenance_draft_plan_entry(entry) for entry in plan.entries],
    }

"""Note mutation and maintenance domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from domain.model_parts.knowledge import AnswerBundle, NoteDocument


NoteChangeAction = Literal["create", "update", "refactor", "archive"]
MaintenanceFindingKind = Literal["empty_note", "sparse_note", "isolated_note", "duplicate_title"]


@dataclass(frozen=True, slots=True)
class NoteChangeProposal:
    """A proposed safe note mutation before any write occurs."""

    action: NoteChangeAction
    target_path: Path
    title: str
    reason: str
    proposed_content: str
    current_content: str | None = None
    archive_path: Path | None = None
    similar_notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AppliedNoteChange:
    """Result of applying a safe note mutation."""

    action: NoteChangeAction
    target_path: Path
    backup_path: Path | None = None
    archive_path: Path | None = None
    applied_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class GeneratedNoteDraft:
    """LLM-generated markdown draft paired with a safe mutation proposal."""

    model: str
    title: str
    instruction: str
    content: str
    proposal: NoteChangeProposal
    citations: tuple[str, ...] = field(default_factory=tuple)
    companion_proposals: tuple[NoteChangeProposal, ...] = field(default_factory=tuple)
    prompt: AnswerBundle | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceFinding:
    """A maintenance issue detected in the knowledge base with an optional safe proposal."""

    kind: MaintenanceFindingKind
    note: NoteDocument
    summary: str
    details: tuple[str, ...] = field(default_factory=tuple)
    proposal: NoteChangeProposal | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceReport:
    """A collection of maintenance findings for the current vault state."""

    findings: tuple[KnowledgeMaintenanceFinding, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenancePlanEntry:
    """A single actionable maintenance step selected for batch review."""

    finding: KnowledgeMaintenanceFinding
    proposal: NoteChangeProposal
    merged_kinds: tuple[MaintenanceFindingKind, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenancePlan:
    """A compact batch of compatible maintenance proposals for review."""

    entries: tuple[KnowledgeMaintenancePlanEntry, ...] = field(default_factory=tuple)
    skipped_paths: tuple[str, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class MaintenanceDraftPlanEntry:
    """A generated maintenance draft attached to its planning context."""

    plan_entry: KnowledgeMaintenancePlanEntry
    draft: GeneratedNoteDraft


@dataclass(frozen=True, slots=True)
class MaintenanceDraftPlan:
    """A review-ready batch of generated maintenance drafts."""

    entries: tuple[MaintenanceDraftPlanEntry, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

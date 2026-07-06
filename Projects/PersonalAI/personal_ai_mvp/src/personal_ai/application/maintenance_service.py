"""Continuous knowledge maintenance heuristics for vault hygiene."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.note_mutation_service import NoteMutationService
from personal_ai.domain.models import (
    KnowledgeMaintenanceFinding,
    KnowledgeMaintenancePlan,
    KnowledgeMaintenancePlanEntry,
    KnowledgeMaintenanceReport,
    NoteDocument,
)


class KnowledgeMaintenanceService:
    """Finds low-quality, isolated, or duplicate notes and proposes safe next steps."""

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        mutation_service: NoteMutationService,
    ) -> None:
        self._knowledge_service = knowledge_service
        self._mutation_service = mutation_service

    def inspect(self) -> KnowledgeMaintenanceReport:
        """Builds a maintenance report for the current vault state."""
        notes = self._knowledge_service.list_notes()
        backlinks = self._build_backlinks(notes)
        findings: list[KnowledgeMaintenanceFinding] = []

        for note in notes:
            findings.extend(self._inspect_note(note, backlinks.get(note.path, 0)))

        findings.extend(self._find_duplicate_titles(notes))
        findings.sort(key=lambda item: (item.note.path.as_posix(), item.kind))
        return KnowledgeMaintenanceReport(findings=tuple(findings))

    def find_finding(
        self,
        note_identifier: str | Path,
        *,
        kind: str | None = None,
    ) -> KnowledgeMaintenanceFinding | None:
        """Finds a single maintenance issue for a note by path or title."""
        requested_path = Path(note_identifier)
        requested_text = str(note_identifier).casefold()

        for finding in self.inspect().findings:
            if kind is not None and finding.kind != kind:
                continue

            note = finding.note
            if note.path == requested_path:
                return finding
            if note.path.as_posix().casefold() == requested_text:
                return finding
            if note.title.casefold() == requested_text:
                return finding

        return None

    def build_plan(
        self,
        *,
        limit: int = 5,
        kinds: tuple[str, ...] = (),
    ) -> KnowledgeMaintenancePlan:
        """Builds a compact batch of compatible maintenance proposals for review."""
        actionable = [
            finding
            for finding in self.inspect().findings
            if finding.proposal is not None
            and not finding.proposal.warnings
            and (not kinds or finding.kind in kinds)
        ]

        grouped: dict[Path, list[KnowledgeMaintenanceFinding]] = defaultdict(list)
        for finding in actionable:
            grouped[finding.note.path].append(finding)

        entries: list[KnowledgeMaintenancePlanEntry] = []
        skipped_paths: list[str] = []
        for path, findings in sorted(grouped.items(), key=lambda item: item[0].as_posix()):
            if len(entries) >= limit:
                skipped_paths.append(path.as_posix())
                continue

            selected = min(findings, key=lambda item: (_finding_priority(item.kind), item.note.path.as_posix()))
            if selected.proposal is None:
                continue
            merged_kinds = tuple(sorted({finding.kind for finding in findings}))
            entries.append(
                KnowledgeMaintenancePlanEntry(
                    finding=selected,
                    proposal=selected.proposal,
                    merged_kinds=merged_kinds,
                )
            )

        return KnowledgeMaintenancePlan(
            entries=tuple(entries),
            skipped_paths=tuple(skipped_paths),
        )

    def _inspect_note(
        self,
        note: NoteDocument,
        backlink_count: int,
    ) -> list[KnowledgeMaintenanceFinding]:
        findings: list[KnowledgeMaintenanceFinding] = []
        body = _note_body(note.content)
        word_count = len(_tokenize_words(body))
        in_inbox = note.path.parts and note.path.parts[0].casefold() == "inbox"

        if word_count == 0:
            proposal = self._mutation_service.propose_change(
                title=note.title,
                proposed_content=note.content,
                action="archive" if in_inbox else "refactor",
                target_path=note.path.as_posix(),
            )
            findings.append(
                KnowledgeMaintenanceFinding(
                    kind="empty_note",
                    note=note,
                    summary="Note has no meaningful body content.",
                    details=(
                        f"path={note.path.as_posix()}",
                        f"word_count={word_count}",
                    ),
                    proposal=proposal,
                )
            )
            return findings

        if word_count < 25:
            proposal = self._mutation_service.propose_change(
                title=note.title,
                proposed_content=note.content,
                action="refactor",
                target_path=note.path.as_posix(),
            )
            findings.append(
                KnowledgeMaintenanceFinding(
                    kind="sparse_note",
                    note=note,
                    summary="Note is very short and may need expansion or consolidation.",
                    details=(
                        f"path={note.path.as_posix()}",
                        f"word_count={word_count}",
                    ),
                    proposal=proposal,
                )
            )

        if not note.links and backlink_count == 0:
            proposal = self._mutation_service.propose_change(
                title=note.title,
                proposed_content=note.content,
                action="refactor",
                target_path=note.path.as_posix(),
            )
            findings.append(
                KnowledgeMaintenanceFinding(
                    kind="isolated_note",
                    note=note,
                    summary="Note is disconnected from the knowledge graph.",
                    details=(
                        f"path={note.path.as_posix()}",
                        "links=0",
                        f"backlinks={backlink_count}",
                    ),
                    proposal=proposal,
                )
            )

        return findings

    def _find_duplicate_titles(
        self,
        notes: list[NoteDocument],
    ) -> list[KnowledgeMaintenanceFinding]:
        grouped: dict[str, list[NoteDocument]] = defaultdict(list)
        for note in notes:
            grouped[_normalize_title(note.title)].append(note)

        findings: list[KnowledgeMaintenanceFinding] = []
        for duplicates in grouped.values():
            if len(duplicates) < 2:
                continue

            duplicate_paths = tuple(sorted(note.path.as_posix() for note in duplicates))
            for note in duplicates:
                findings.append(
                    KnowledgeMaintenanceFinding(
                        kind="duplicate_title",
                        note=note,
                        summary="Multiple notes share the same normalized title.",
                        details=duplicate_paths,
                        proposal=None,
                    )
                )

        return findings

    def _build_backlinks(self, notes: list[NoteDocument]) -> dict[Path, int]:
        backlinks: dict[Path, int] = defaultdict(int)
        by_title = {_normalize_title(note.title): note.path for note in notes}
        by_stem = {_normalize_title(note.path.stem): note.path for note in notes}

        for note in notes:
            for link in note.links:
                key = _normalize_title(Path(link.target).stem)
                target_path = by_title.get(key) or by_stem.get(key)
                if target_path is not None:
                    backlinks[target_path] += 1

        return backlinks


def _note_body(content: str) -> str:
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.casefold())


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _finding_priority(kind: str) -> int:
    priorities = {
        "empty_note": 0,
        "sparse_note": 1,
        "isolated_note": 2,
        "duplicate_title": 3,
    }
    return priorities.get(kind, 99)

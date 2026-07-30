"""Safe proposal and apply pipeline for note creation and updates."""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from application.knowledge.knowledge_service import KnowledgeService
from application.notes.policy import NotePolicy
from domain.models import AppliedNoteChange, NoteChangeAction, NoteChangeProposal


class NoteMutationService:
    """Builds and applies safe note mutations with history preservation."""

    def __init__(self, knowledge_service: KnowledgeService, policy: NotePolicy) -> None:
        self._knowledge_service = knowledge_service
        self._policy = policy
        self._vault_root = knowledge_service.vault_root

    def propose_change(
        self,
        *,
        title: str,
        proposed_content: str,
        action: NoteChangeAction | None = None,
        target_dir: str | None = None,
        target_path: str | None = None,
    ) -> NoteChangeProposal:
        """Builds a safe note change proposal without writing to disk."""
        explicit_action = action
        existing_note = None

        if target_path:
            existing_note = self._knowledge_service.get_note(Path(target_path))
        if existing_note is None:
            existing_note = self._knowledge_service.get_note(title)

        resolved_action = explicit_action or ("update" if existing_note is not None else "create")
        resolved_target = self._resolve_target_path(
            title=title,
            target_dir=target_dir,
            target_path=target_path,
            existing_path=existing_note.path if existing_note is not None else None,
        )

        allowed, policy_warnings = self._policy.validate_target(resolved_target)
        warnings = list(policy_warnings)

        if resolved_action == "create" and existing_note is not None:
            warnings.append("A note with the same title already exists; update may be safer.")
        if resolved_action in {"update", "refactor", "archive"} and existing_note is None:
            warnings.append("No existing note was found for the requested update/refactor/archive.")
        if not allowed:
            warnings.append("Policy validation failed for the requested target.")

        similar_notes = self._find_similar_notes(title, resolved_target, existing_note.path if existing_note else None)
        if similar_notes and resolved_action == "create":
            warnings.append("Similar notes exist; review whether create is necessary.")

        archive_path = None
        if resolved_action == "archive":
            archive_path = self._build_archive_path(resolved_target)

        return NoteChangeProposal(
            action=resolved_action,
            target_path=resolved_target,
            title=title,
            reason=self._build_reason(resolved_action, existing_note is not None),
            proposed_content=proposed_content,
            current_content=existing_note.content if existing_note is not None else None,
            archive_path=archive_path,
            similar_notes=similar_notes,
            warnings=tuple(warnings),
        )

    def apply_change(self, proposal: NoteChangeProposal, *, approved: bool = False) -> AppliedNoteChange:
        """Applies a previously built proposal after explicit approval."""
        if not approved:
            raise RuntimeError("Explicit approval is required before applying note changes.")
        if proposal.warnings:
            raise RuntimeError("Proposal contains warnings. Resolve them before applying changes.")

        target = self._vault_root / proposal.target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = None

        if proposal.action in {"update", "refactor", "archive"}:
            if not target.exists():
                raise RuntimeError("Target note does not exist.")
            backup_path = self._create_backup(target, proposal.target_path)

        if proposal.action == "create":
            if target.exists():
                raise RuntimeError("Target note already exists.")
            target.write_text(proposal.proposed_content, encoding="utf-8")
        elif proposal.action in {"update", "refactor"}:
            target.write_text(proposal.proposed_content, encoding="utf-8")
        elif proposal.action == "archive":
            if proposal.archive_path is None:
                raise RuntimeError("Archive path is missing from proposal.")
            archive_target = self._vault_root / proposal.archive_path
            archive_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(archive_target))
        else:
            raise RuntimeError(f"Unsupported action: {proposal.action}")

        self._knowledge_service.load()
        return AppliedNoteChange(
            action=proposal.action,
            target_path=proposal.target_path,
            backup_path=backup_path,
            archive_path=proposal.archive_path,
        )

    def build_note_lookup(self) -> dict[str, str]:
        """Builds a vault-wide lookup for note titles and common path forms."""
        lookup: dict[str, str] = {}
        for note in self._knowledge_service.list_notes():
            title = note.title
            lookup[note.title.casefold()] = title
            lookup[note.path.as_posix().casefold()] = title
            lookup[note.path.stem.casefold()] = title
            lookup[note.path.name.casefold()] = title
        return lookup

    def _resolve_target_path(
        self,
        *,
        title: str,
        target_dir: str | None,
        target_path: str | None,
        existing_path: Path | None,
    ) -> Path:
        if target_path:
            path = Path(target_path)
            return path if path.suffix else path.with_suffix(".md")
        if existing_path is not None:
            return existing_path

        filename = f"{_sanitize_filename(title)}.md"
        if target_dir:
            return Path(target_dir) / filename
        return Path("Inbox") / filename

    def _build_archive_path(self, target_path: Path) -> Path:
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        return Path("Archive") / stamp / target_path

    def _create_backup(self, absolute_path: Path, relative_path: Path) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        backup_path = self._vault_root / ".history" / stamp / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(absolute_path, backup_path)
        return backup_path.relative_to(self._vault_root)

    def _build_reason(self, action: NoteChangeAction, has_existing_note: bool) -> str:
        if action == "create":
            return "Create a new note because no exact existing note was found."
        if action == "update":
            return "Update an existing note because related knowledge already exists."
        if action == "refactor":
            return "Refactor an existing note to improve structure while preserving history."
        if action == "archive":
            return "Archive obsolete knowledge while preserving history."
        return "Apply a note mutation."

    def _find_similar_notes(
        self,
        title: str,
        target_path: Path,
        existing_path: Path | None,
    ) -> tuple[str, ...]:
        title_key = _normalize_key(title)
        target_stem_key = _normalize_key(target_path.stem)
        matches: list[str] = []

        for note in self._knowledge_service.list_notes():
            if existing_path is not None and note.path == existing_path:
                continue

            note_title_key = _normalize_key(note.title)
            note_stem_key = _normalize_key(note.path.stem)
            if title_key and title_key in {note_title_key, note_stem_key}:
                matches.append(note.path.as_posix())
                continue

            if target_stem_key and target_stem_key in {note_title_key, note_stem_key}:
                matches.append(note.path.as_posix())

        return tuple(sorted(set(matches)))


def _sanitize_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "-", title).strip()
    return cleaned or "Untitled"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())

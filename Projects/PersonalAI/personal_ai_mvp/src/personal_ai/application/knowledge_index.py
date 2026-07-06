"""In-memory note index and query APIs."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from personal_ai.domain.models import NoteDocument


class KnowledgeIndex:
    """Maintains in-memory note lookup tables and relationships."""

    def __init__(self, notes: list[NoteDocument] | None = None) -> None:
        self._notes_by_path: dict[Path, NoteDocument] = {}
        self._notes_by_title: dict[str, NoteDocument] = {}
        self._relationships: dict[Path, set[Path]] = defaultdict(set)

        for note in notes or []:
            self.add_note(note)

    def add_note(self, note: NoteDocument) -> None:
        """Adds or replaces a note in the index."""
        normalized_path = note.path.as_posix().lower()
        previous = next(
            (path for path in self._notes_by_path if path.as_posix().lower() == normalized_path),
            None,
        )
        if previous is not None:
            self._notes_by_path.pop(previous)
            self._relationships.pop(previous, None)

        self._notes_by_path[note.path] = note
        self._notes_by_title[note.title.casefold()] = note
        self._rebuild_relationships()

    def get_note(self, identifier: str | Path) -> NoteDocument | None:
        """Returns a note by path or title."""
        if isinstance(identifier, Path):
            return self._notes_by_path.get(identifier)

        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            return None

        path = Path(identifier)
        if path.suffix == ".md" or "/" in identifier or "\\" in identifier:
            direct = self._notes_by_path.get(path)
            if direct is not None:
                return direct

            normalized = path.as_posix().lower()
            for known_path, note in self._notes_by_path.items():
                if known_path.as_posix().lower() == normalized:
                    return note

        title_match = self._notes_by_title.get(normalized_identifier.casefold())
        if title_match is not None:
            return title_match

        stem = Path(normalized_identifier).stem.casefold()
        for known_path, note in self._notes_by_path.items():
            if known_path.stem.casefold() == stem:
                return note

        return None

    def list_notes(self) -> list[NoteDocument]:
        """Returns all indexed notes sorted by path."""
        return [self._notes_by_path[path] for path in sorted(self._notes_by_path)]

    def search_notes(self, query: str) -> list[NoteDocument]:
        """Performs simple case-insensitive title and content search."""
        needle = query.casefold().strip()
        if not needle:
            return self.list_notes()

        matches: list[NoteDocument] = []
        for note in self.list_notes():
            if needle in note.title.casefold() or needle in note.content.casefold():
                matches.append(note)
        return matches

    def get_related_notes(self, identifier: str | Path) -> list[NoteDocument]:
        """Returns notes referenced by the target note."""
        note = self.get_note(identifier)
        if note is None:
            return []

        related_paths = sorted(self._relationships.get(note.path, set()))
        return [self._notes_by_path[path] for path in related_paths if path in self._notes_by_path]

    def _resolve_relationships(self, note: NoteDocument) -> set[Path]:
        related: set[Path] = set()
        for link in note.links:
            target = self._find_path_for_link(link.target)
            if target is not None:
                related.add(target)
        return related

    def _rebuild_relationships(self) -> None:
        self._relationships = defaultdict(set)
        for note in self._notes_by_path.values():
            self._relationships[note.path] = self._resolve_relationships(note)

    def _find_path_for_link(self, target: str) -> Path | None:
        normalized_target = target.strip()
        if not normalized_target:
            return None

        path_candidate = Path(normalized_target)
        if path_candidate.suffix != ".md":
            path_candidate = path_candidate.with_suffix(".md")

        for known_path in self._notes_by_path:
            if known_path.as_posix().casefold() == path_candidate.as_posix().casefold():
                return known_path
            if known_path.stem.casefold() == Path(normalized_target).stem.casefold():
                return known_path
        return None

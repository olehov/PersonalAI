"""Application service for deterministic directory-level knowledge analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re

from application.knowledge.knowledge_service import KnowledgeService
from domain.models import (
    DirectoryAnalysisNodeStat,
    DirectoryAnalysisReport,
    DirectoryCoverageSuggestion,
    NoteDocument,
)


_DIRECTORY_TOPIC_CATALOG: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "Languages/C": (
        ("Build and Tooling for C", ("make", "cmake", "build", "toolchain")),
        ("Strings and Character Arrays in C", ("string", "strlen", "strcpy", "memcpy")),
        ("Structs and Unions in C", ("struct", "union")),
        ("Processes and Signals in C", ("fork", "exec", "signal", "process")),
        ("Sockets in C", ("socket", "bind", "listen", "connect", "recv", "send")),
        ("Testing and Debugging C Programs", ("testing", "debug", "gdb", "sanitizer", "valgrind")),
        ("Undefined Behavior in C", ("undefined behavior", "ub", "aliasing", "overflow")),
    ),
}


class DirectoryAnalysisService:
    """Analyzes one vault directory as a note inventory plus local graph slice."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self._knowledge_service = knowledge_service

    def analyze_directory(self, directory: str | Path) -> DirectoryAnalysisReport:
        """Builds a deterministic report for notes stored under one directory."""
        directory_path = self._normalize_directory(directory)
        notes = tuple(self._select_notes(directory_path))
        note_paths = {note.path for note in notes}

        inbound_counts: Counter[Path] = Counter()
        outbound_counts: Counter[Path] = Counter()
        unresolved_counter: Counter[str] = Counter()
        total_links = 0
        internal_links = 0
        cross_directory_links = 0

        for note in notes:
            for link in note.links:
                total_links += 1
                resolved = self._knowledge_service.get_note(link.target)
                if resolved is None:
                    unresolved_counter[link.target] += 1
                    continue
                if resolved.path in note_paths:
                    internal_links += 1
                    outbound_counts[note.path] += 1
                    inbound_counts[resolved.path] += 1
                else:
                    cross_directory_links += 1

        isolated_notes = tuple(
            sorted(
                (
                    note.path
                    for note in notes
                    if inbound_counts[note.path] == 0 and outbound_counts[note.path] == 0
                ),
                key=lambda path: path.as_posix().lower(),
            )
        )
        hub_notes = tuple(
            sorted(
                (
                    DirectoryAnalysisNodeStat(
                        note=note,
                        inbound_links=inbound_counts[note.path],
                        outbound_links=outbound_counts[note.path],
                    )
                    for note in notes
                    if inbound_counts[note.path] > 0 or outbound_counts[note.path] > 0
                ),
                key=lambda item: (
                    -(item.inbound_links + item.outbound_links),
                    -item.inbound_links,
                    item.note.title.lower(),
                ),
            )[:5]
        )

        suggestions = self._build_suggestions(
            directory_path=directory_path,
            notes=notes,
            unresolved_counter=unresolved_counter,
            isolated_notes=isolated_notes,
        )

        return DirectoryAnalysisReport(
            directory=directory_path,
            note_count=len(notes),
            notes=tuple(sorted(notes, key=lambda note: note.path.as_posix().lower())),
            total_links=total_links,
            internal_link_count=internal_links,
            cross_directory_link_count=cross_directory_links,
            unresolved_links=tuple(
                target
                for target, _ in sorted(
                    unresolved_counter.items(),
                    key=lambda item: (-item[1], item[0].lower()),
                )
            ),
            isolated_notes=isolated_notes,
            hub_notes=hub_notes,
            suggestions=suggestions,
        )

    def _normalize_directory(self, directory: str | Path) -> Path:
        if isinstance(directory, Path):
            return Path(*directory.parts)
        cleaned = str(directory).replace("\\", "/").strip().strip("/")
        return Path(cleaned) if cleaned else Path(".")

    def _select_notes(self, directory_path: Path) -> list[NoteDocument]:
        prefix = directory_path.as_posix().lower().strip("/")
        if prefix in {"", "."}:
            return self._knowledge_service.list_notes()

        return [
            note
            for note in self._knowledge_service.list_notes()
            if note.path.as_posix().lower().startswith(f"{prefix}/")
        ]

    def _build_suggestions(
        self,
        *,
        directory_path: Path,
        notes: tuple[NoteDocument, ...],
        unresolved_counter: Counter[str],
        isolated_notes: tuple[Path, ...],
    ) -> tuple[DirectoryCoverageSuggestion, ...]:
        suggestions: list[DirectoryCoverageSuggestion] = []
        existing_titles = {self._normalize_text(note.title) for note in notes}
        corpus = " ".join(f"{note.title}\n{note.content}" for note in notes).lower()

        for target, count in sorted(
            unresolved_counter.items(),
            key=lambda item: (-item[1], item[0].lower()),
        ):
            title = self._sanitize_link_target(target)
            if not title or self._normalize_text(title) in existing_titles:
                continue
            suggestions.append(
                DirectoryCoverageSuggestion(
                    title=title,
                    reason=(
                        f"Referenced {count} time(s) from this directory but no matching note was found."
                    ),
                    source="dangling_link",
                )
            )

        catalog = _DIRECTORY_TOPIC_CATALOG.get(directory_path.as_posix())
        if catalog is not None:
            for title, keywords in catalog:
                normalized_title = self._normalize_text(title)
                if normalized_title in existing_titles:
                    continue
                if any(keyword in corpus for keyword in keywords):
                    continue
                suggestions.append(
                    DirectoryCoverageSuggestion(
                        title=title,
                        reason=(
                            f"Useful foundational coverage for {directory_path.as_posix()} is missing."
                        ),
                        source="topic_catalog",
                    )
                )

        if len(isolated_notes) >= 2 and notes:
            directory_name = directory_path.name if directory_path.name else "Vault"
            overview_title = f"{directory_name} Overview"
            if self._normalize_text(overview_title) not in existing_titles:
                suggestions.append(
                    DirectoryCoverageSuggestion(
                        title=overview_title,
                        reason="Several notes are isolated; an overview note could connect them with explicit links.",
                        source="graph_gap",
                    )
                )

        deduped: dict[str, DirectoryCoverageSuggestion] = {}
        for suggestion in suggestions:
            key = self._normalize_text(suggestion.title)
            deduped.setdefault(key, suggestion)

        return tuple(deduped.values())

    def _sanitize_link_target(self, target: str) -> str:
        cleaned = target.split("#", maxsplit=1)[0].strip()
        cleaned = cleaned.split("|", maxsplit=1)[0].strip()
        cleaned = Path(cleaned).stem
        return cleaned

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

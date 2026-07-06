"""Obsidian vault reader that builds structured note documents."""

from __future__ import annotations

import re
from pathlib import Path

from personal_ai.application.note_policy import NotePolicy
from personal_ai.domain.models import NoteDocument, NoteLink, NoteMetadata
from personal_ai.infrastructure.frontmatter import parse_frontmatter

OBSIDIAN_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


class VaultReader:
    """Reads markdown notes from an Obsidian vault."""

    def __init__(self, vault_root: Path) -> None:
        self._vault_root = vault_root.resolve()

    def read_all(self) -> list[NoteDocument]:
        """Recursively scans the vault and returns all markdown notes."""
        notes: list[NoteDocument] = []
        for path in sorted(self._vault_root.rglob("*.md")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(self._vault_root)
            if NotePolicy.is_restricted_relative_path(relative_path):
                continue
            notes.append(self.read_note(path))
        return notes

    def read_note(self, path: Path) -> NoteDocument:
        """Reads a single markdown note and returns its structured form."""
        resolved_path = path.resolve() if path.is_absolute() else (self._vault_root / path).resolve()
        raw_text = resolved_path.read_text(encoding="utf-8")
        metadata_values, content = parse_frontmatter(raw_text)
        relative_path = resolved_path.relative_to(self._vault_root)
        title = self._extract_title(relative_path, content)
        links = tuple(self._extract_links(content))

        return NoteDocument(
            path=relative_path,
            title=title,
            content=content,
            metadata=NoteMetadata(metadata_values),
            links=links,
        )

    def _extract_title(self, relative_path: Path, content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return relative_path.stem

    def _extract_links(self, content: str) -> list[NoteLink]:
        links: list[NoteLink] = []
        for match in OBSIDIAN_LINK_PATTERN.finditer(content):
            raw = match.group(1).strip()
            target, alias = self._split_link(raw)
            links.append(NoteLink(raw=raw, target=target, alias=alias))
        return links

    def _split_link(self, raw: str) -> tuple[str, str | None]:
        target_with_heading, _, alias = raw.partition("|")
        target, _, _heading = target_with_heading.partition("#")
        normalized_target = target.strip()
        normalized_alias = alias.strip() or None
        return normalized_target, normalized_alias

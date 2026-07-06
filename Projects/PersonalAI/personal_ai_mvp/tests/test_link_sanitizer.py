from __future__ import annotations

import unittest
from pathlib import Path

from personal_ai.application.link_sanitizer import (
    build_note_lookup,
    find_unsupported_obsidian_links,
    sanitize_generated_links,
)
from personal_ai.domain.models import NoteDocument, NoteLink, NoteMetadata


class LinkSanitizerTests(unittest.TestCase):
    def test_sanitize_generated_links_normalizes_known_targets_and_prunes_unknown_ones(self) -> None:
        lookup = build_note_lookup(
            (
                NoteDocument(
                    path=Path("Projects/PersonalAI Roadmap.md"),
                    title="PersonalAI Roadmap",
                    content="# PersonalAI Roadmap\n",
                    metadata=NoteMetadata(values={}),
                    links=(),
                ),
                NoteDocument(
                    path=Path("Languages/C/File IO in C.md"),
                    title="File IO in C",
                    content="# File IO in C\n",
                    metadata=NoteMetadata(values={}),
                    links=(),
                ),
            )
        )

        sanitized = sanitize_generated_links(
            (
                "- [Roadmap](Projects/PersonalAI Roadmap.md)\n"
                "- [[Languages/C/File IO in C.md|file io]]\n"
                "- [[Imaginary Note]]\n"
            ),
            lookup,
        )

        self.assertIn("[[PersonalAI Roadmap|Roadmap]]", sanitized)
        self.assertIn("[[File IO in C|file io]]", sanitized)
        self.assertNotIn("[[Imaginary Note]]", sanitized)
        self.assertIn("- Imaginary Note", sanitized)

    def test_find_unsupported_obsidian_links_reports_only_missing_targets(self) -> None:
        lookup = build_note_lookup(
            (
                NoteDocument(
                    path=Path("Linux/Processes and Signals.md"),
                    title="Processes and Signals",
                    content="# Processes and Signals\n",
                    metadata=NoteMetadata(values={}),
                    links=(NoteLink(raw="Job Control", target="Job Control", alias=None),),
                ),
            )
        )

        unsupported = find_unsupported_obsidian_links(
            (
                "[[Processes and Signals]]\n"
                "[[Kernel Queues]]\n"
                "[[Kernel Queues|queues]]\n"
            ),
            lookup,
        )

        self.assertEqual(unsupported, ("Kernel Queues",))


if __name__ == "__main__":
    unittest.main()

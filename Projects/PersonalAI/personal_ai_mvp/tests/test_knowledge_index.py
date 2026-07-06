from __future__ import annotations

import unittest
from pathlib import Path

from personal_ai.application.knowledge_index import KnowledgeIndex
from personal_ai.domain.models import NoteDocument, NoteLink, NoteMetadata


class KnowledgeIndexTests(unittest.TestCase):
    def test_supports_lookup_search_and_relationships(self) -> None:
        architecture = NoteDocument(
            path=Path("Projects/PersonalAI/Architecture.md"),
            title="Architecture",
            content="Core design for the assistant.",
            metadata=NoteMetadata({"type": "project"}),
            links=(NoteLink(raw="Vision", target="Vision", alias=None),),
        )
        vision = NoteDocument(
            path=Path("Projects/PersonalAI/Vision.md"),
            title="Vision",
            content="Long-term product direction.",
            metadata=NoteMetadata({"type": "project"}),
            links=(),
        )

        index = KnowledgeIndex([architecture, vision])

        self.assertIs(index.get_note("Vision"), vision)
        self.assertIs(index.get_note(Path("Projects/PersonalAI/Architecture.md")), architecture)
        self.assertEqual(index.search_notes("product"), [vision])
        self.assertEqual(index.get_related_notes("Architecture"), [vision])
        self.assertEqual(
            [note.title for note in index.list_notes()],
            ["Architecture", "Vision"],
        )

    def test_returns_empty_results_for_unknown_notes(self) -> None:
        index = KnowledgeIndex()

        self.assertIsNone(index.get_note("missing"))
        self.assertEqual(index.get_related_notes("missing"), [])
        self.assertEqual(index.search_notes("missing"), [])


if __name__ == "__main__":
    unittest.main()

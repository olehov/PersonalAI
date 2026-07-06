from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.note_mutation_service import NoteMutationService
from personal_ai.application.note_policy import NotePolicy


class NoteMutationServiceTests(unittest.TestCase):
    def test_propose_update_for_existing_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Heap.md").write_text("# Heap\nOld\n", encoding="utf-8")

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = NoteMutationService(knowledge, NotePolicy(root))
            proposal = service.propose_change(title="Heap", proposed_content="# Heap\nNew\n")

            self.assertEqual(proposal.action, "update")
            self.assertEqual(proposal.target_path, Path("Algorithms/Heap.md"))
            self.assertEqual(proposal.current_content, "# Heap\nOld\n")
            self.assertEqual(proposal.warnings, ())

    def test_apply_update_creates_history_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            note_path = root / "Algorithms" / "Heap.md"
            note_path.write_text("# Heap\nOld\n", encoding="utf-8")

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = NoteMutationService(knowledge, NotePolicy(root))
            proposal = service.propose_change(title="Heap", proposed_content="# Heap\nNew\n")
            change = service.apply_change(proposal, approved=True)

            self.assertEqual(note_path.read_text(encoding="utf-8"), "# Heap\nNew\n")
            self.assertIsNotNone(change.backup_path)
            backup = root / change.backup_path
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "# Heap\nOld\n")
            self.assertEqual(
                sorted(note.path.as_posix() for note in knowledge.list_notes()),
                ["Algorithms/Heap.md"],
            )

    def test_apply_archive_moves_note_and_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Inbox").mkdir()
            note_path = root / "Inbox" / "Draft.md"
            note_path.write_text("# Draft\nObsolete\n", encoding="utf-8")

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = NoteMutationService(knowledge, NotePolicy(root))
            proposal = service.propose_change(
                title="Draft",
                proposed_content="# Draft\nObsolete\n",
                action="archive",
            )
            change = service.apply_change(proposal, approved=True)

            self.assertFalse(note_path.exists())
            self.assertIsNotNone(change.archive_path)
            self.assertTrue((root / change.archive_path).exists())
            self.assertIsNotNone(change.backup_path)
            self.assertTrue((root / change.backup_path).exists())

    def test_restricted_target_generates_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            knowledge = KnowledgeService(root)
            knowledge.load()
            service = NoteMutationService(knowledge, NotePolicy(root))
            proposal = service.propose_change(
                title="Secret",
                proposed_content="# Secret\n",
                target_path=".obsidian/Secret.md",
                action="create",
            )

            self.assertTrue(proposal.warnings)
            self.assertIn("restricted area", proposal.warnings[0])

    def test_create_is_not_blocked_by_meta_mentions_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture Decisions").mkdir()
            (root / "Architecture Decisions" / "Knowledge Management.md").write_text(
                "# Knowledge Management\nExamples:\n- Heap\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = NoteMutationService(knowledge, NotePolicy(root))
            proposal = service.propose_change(
                title="Heap",
                proposed_content="# Heap\nFoundational note.\n",
                target_dir="Algorithms",
                action="create",
            )

            self.assertEqual(proposal.similar_notes, ())
            self.assertEqual(proposal.warnings, ())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_ai.application.knowledge_service import (
    KnowledgeService,
    serialize_maintenance_report,
)
from personal_ai.application.maintenance_service import KnowledgeMaintenanceService
from personal_ai.application.note_mutation_service import NoteMutationService
from personal_ai.application.note_policy import NotePolicy


class KnowledgeMaintenanceServiceTests(unittest.TestCase):
    def test_inspect_detects_empty_inbox_note_for_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Inbox").mkdir()
            (root / "Inbox" / "Scratch.md").write_text("# Scratch\n", encoding="utf-8")

            knowledge = KnowledgeService(root)
            knowledge.load()
            mutation = NoteMutationService(knowledge, NotePolicy(root))
            report = KnowledgeMaintenanceService(knowledge, mutation).inspect()
            payload = serialize_maintenance_report(report)

            self.assertEqual(payload["findings"][0]["kind"], "empty_note")
            self.assertEqual(payload["findings"][0]["proposal"]["action"], "archive")

    def test_inspect_detects_isolated_and_sparse_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Stub.md").write_text(
                "# Stub\nTiny isolated note.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            mutation = NoteMutationService(knowledge, NotePolicy(root))
            report = KnowledgeMaintenanceService(knowledge, mutation).inspect()
            payload = serialize_maintenance_report(report)

            kinds = {finding["kind"] for finding in payload["findings"]}
            self.assertIn("sparse_note", kinds)
            self.assertIn("isolated_note", kinds)

    def test_inspect_detects_duplicate_titles_without_auto_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Inbox").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nMain heap note with enough words to avoid sparse warnings in this test.\n",
                encoding="utf-8",
            )
            (root / "Inbox" / "Heap.md").write_text(
                "# Heap\nDuplicate heap draft with enough words for duplicate detection only.\n[[Heap]]\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            mutation = NoteMutationService(knowledge, NotePolicy(root))
            report = KnowledgeMaintenanceService(knowledge, mutation).inspect()
            payload = serialize_maintenance_report(report)

            duplicate_findings = [
                finding for finding in payload["findings"] if finding["kind"] == "duplicate_title"
            ]
            self.assertEqual(len(duplicate_findings), 2)
            self.assertTrue(all(finding["proposal"] is None for finding in duplicate_findings))

    def test_build_plan_merges_findings_per_note_and_respects_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "MVP.md").write_text(
                "# MVP\n## Goal\nShort.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            mutation = NoteMutationService(knowledge, NotePolicy(root))
            plan = KnowledgeMaintenanceService(knowledge, mutation).build_plan(limit=1)

            self.assertEqual(len(plan.entries), 1)
            self.assertEqual(plan.entries[0].finding.note.path.as_posix(), "Projects/PersonalAI/MVP.md")
            self.assertIn("sparse_note", plan.entries[0].merged_kinds)
            self.assertTrue(plan.skipped_paths)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.cli_test_support import CliTestSupport


class NoteCliTests(CliTestSupport):
    def test_propose_note_outputs_json_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as temp_file:
                temp_file.write("# Heap\nDetails\n")
                content_file = Path(temp_file.name)

            try:
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "propose-note",
                        "--title",
                        "Heap",
                        "--content-file",
                        str(content_file),
                        "--target-dir",
                        "Algorithms",
                    ]
                )
            finally:
                content_file.unlink(missing_ok=True)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["action"], "create")
            self.assertEqual(payload["target_path"], "Algorithms/Heap.md")

    def test_draft_note_outputs_generated_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch(
                "application.notes.draft_service.NoteDraftService.draft_note",
                return_value=type(
                    "Draft",
                    (),
                    {
                        "model": "llama3:latest",
                        "title": "Heap",
                        "instruction": "Create a heap note.",
                        "content": "# Heap\nDraft\n",
                        "citations": ("Algorithms/Binary Search.md",),
                        "prompt": None,
                        "proposal": type(
                            "Proposal",
                            (),
                            {
                                "action": "create",
                                "target_path": Path("Algorithms/Heap.md"),
                                "title": "Heap",
                                "reason": "Create a new note because no exact existing note was found.",
                                "proposed_content": "# Heap\nDraft\n",
                                "current_content": None,
                                "archive_path": None,
                                "similar_notes": (),
                                "warnings": (),
                                "created_at": self._now(),
                            },
                        )(),
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "draft-note",
                        "--title",
                        "Heap",
                        "--instruction",
                        "Create a heap note.",
                        "--target-dir",
                        "Algorithms",
                        "--model",
                        "llama3:latest",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["proposal"]["action"], "create")
            self.assertTrue(payload["content"].startswith("# Heap"))

    def test_retrieve_accepts_scope_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Projects").mkdir()
            (root / "Algorithms" / "Heap.md").write_text("# Heap\nComplexity.\n", encoding="utf-8")
            (root / "Projects" / "Heap.md").write_text("# Heap Project\nRoadmap.\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "retrieve",
                    "heap complexity",
                    "--scope-dir",
                    "Algorithms",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["primary_notes"][0]["note"]["path"], "Algorithms/Heap.md")

    def test_analyze_dir_outputs_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Languages" / "C" / "File IO in C.md").write_text(
                "# File I/O in C\n[[Error Handling in C]]\n[[stdio]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Error Handling in C.md").write_text(
                "# Error Handling in C\n[[File IO in C]]\n",
                encoding="utf-8",
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "analyze-dir",
                    "Languages/C",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["directory"], "Languages/C")
            self.assertEqual(payload["note_count"], 2)
            self.assertIn("stdio", payload["unresolved_links"])
            self.assertEqual(payload["hub_notes"][0]["note"]["title"], "Error Handling in C")

    def test_maintenance_outputs_json_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Inbox").mkdir()
            (root / "Inbox" / "Scratch.md").write_text("# Scratch\n", encoding="utf-8")

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "maintenance",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["findings"][0]["kind"], "empty_note")
            self.assertEqual(payload["findings"][0]["proposal"]["action"], "archive")

    def test_maintenance_plan_outputs_json_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "MVP.md").write_text(
                "# MVP\n## Goal\nShort.\n",
                encoding="utf-8",
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "maintenance-plan",
                    "--limit",
                    "1",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["finding"]["note"]["path"], "Projects/PersonalAI/MVP.md")

    def test_maintenance_plan_draft_outputs_json_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch(
                "application.notes.draft_service.NoteDraftService.draft_maintenance_plan",
                return_value=type(
                    "DraftPlan",
                    (),
                    {
                        "generated_at": self._now(),
                        "entries": (
                            type(
                                "Entry",
                                (),
                                {
                                    "plan_entry": type(
                                        "PlanEntry",
                                        (),
                                        {
                                            "finding": type(
                                                "Finding",
                                                (),
                                                {
                                                    "kind": "sparse_note",
                                                    "summary": "Short note.",
                                                    "details": (),
                                                    "note": type(
                                                        "Note",
                                                        (),
                                                        {
                                                            "path": Path("Projects/Vision.md"),
                                                            "title": "Vision",
                                                            "content": "# Vision\n",
                                                            "metadata": type("Metadata", (), {"values": {}})(),
                                                            "links": (),
                                                        },
                                                    )(),
                                                    "proposal": None,
                                                },
                                            )(),
                                            "proposal": type(
                                                "Proposal",
                                                (),
                                                {
                                                    "action": "refactor",
                                                    "target_path": Path("Projects/Vision.md"),
                                                    "title": "Vision",
                                                    "reason": "Refactor.",
                                                    "proposed_content": "# Vision\n## Goal\nExpanded.\n",
                                                    "current_content": "# Vision\n",
                                                    "archive_path": None,
                                                    "similar_notes": (),
                                                    "warnings": (),
                                                    "created_at": self._now(),
                                                },
                                            )(),
                                            "merged_kinds": ("sparse_note",),
                                        },
                                    )(),
                                    "draft": type(
                                        "Draft",
                                        (),
                                        {
                                            "model": "llama3:latest",
                                            "title": "Vision",
                                            "instruction": "Maintenance refactor: Short note.",
                                            "content": "# Vision\n## Goal\nExpanded.\n",
                                            "citations": ("Projects/Vision.md",),
                                            "prompt": None,
                                            "proposal": type(
                                                "Proposal",
                                                (),
                                                {
                                                    "action": "refactor",
                                                    "target_path": Path("Projects/Vision.md"),
                                                    "title": "Vision",
                                                    "reason": "Refactor.",
                                                    "proposed_content": "# Vision\n## Goal\nExpanded.\n",
                                                    "current_content": "# Vision\n",
                                                    "archive_path": None,
                                                    "similar_notes": (),
                                                    "warnings": (),
                                                    "created_at": self._now(),
                                                },
                                            )(),
                                            "companion_proposals": (),
                                        },
                                    )(),
                                },
                            )(),
                        ),
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "maintenance-plan-draft",
                        "--limit",
                        "1",
                        "--model",
                        "llama3:latest",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload["entries"]), 1)
            self.assertEqual(payload["entries"][0]["draft"]["proposal"]["target_path"], "Projects/Vision.md")

    def test_maintenance_draft_outputs_generated_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Vision.md").write_text("# Vision\nShort note.\n", encoding="utf-8")

            with patch(
                "application.notes.draft_service.NoteDraftService.draft_maintenance_finding",
                return_value=type(
                    "Draft",
                    (),
                    {
                        "model": "llama3:latest",
                        "title": "Vision",
                        "instruction": "Maintenance refactor: expand sparse note",
                        "content": "# Vision\n## Goal\nExpanded.\n",
                        "citations": ("Projects/Vision.md",),
                        "prompt": None,
                        "proposal": type(
                            "Proposal",
                            (),
                            {
                                "action": "refactor",
                                "target_path": Path("Projects/Vision.md"),
                                "title": "Vision",
                                "reason": "Refactor an existing note to improve structure while preserving history.",
                                "proposed_content": "# Vision\n## Goal\nExpanded.\n",
                                "current_content": "# Vision\nShort note.\n",
                                "archive_path": None,
                                "similar_notes": (),
                                "warnings": (),
                                "created_at": self._now(),
                            },
                        )(),
                    },
                )(),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "maintenance-draft",
                        "--note",
                        "Projects/Vision.md",
                        "--kind",
                        "sparse_note",
                        "--model",
                        "llama3:latest",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["proposal"]["action"], "refactor")
            self.assertEqual(payload["proposal"]["target_path"], "Projects/Vision.md")

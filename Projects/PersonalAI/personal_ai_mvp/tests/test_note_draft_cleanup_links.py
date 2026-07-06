from __future__ import annotations

import tempfile
from pathlib import Path

from tests.note_draft_test_support import NoteDraftServiceTestSupport


class NoteDraftCleanupLinksTests(NoteDraftServiceTestSupport):
    def test_generated_note_cleanup_removes_meta_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\nShort note.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Core\n"
                    "- Python\n\n"
                    "Grounded context:\n"
                    "[[Roadmap]] matters here.\n"
                    "This note should be expanded with more detail.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("Grounded context:", draft.content)
            self.assertNotIn("This note should be expanded", draft.content)
            self.assertTrue(draft.content.endswith("\n"))

    def test_generated_note_cleanup_normalizes_link_style(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\nShort note.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nPlan.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "* Core item\n"
                    "[[Projects/Roadmap.md|Roadmap]]\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("- Core item", draft.content)
            self.assertIn("[[PersonalAI Roadmap|Roadmap]]", draft.content)
            self.assertNotIn("[[Projects/Roadmap.md|Roadmap]]", draft.content)

    def test_generated_note_cleanup_removes_unknown_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\nShort note.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "- [[Knowledge Graphs]] can help.\n"
                    "- [[Unknown Concept|custom alias]] may appear.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("[[Knowledge Graphs]]", draft.content)
            self.assertNotIn("[[Unknown Concept|custom alias]]", draft.content)
            self.assertIn("- Knowledge Graphs can help.", draft.content)
            self.assertIn("- custom alias may appear.", draft.content)

    def test_generated_note_cleanup_normalizes_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\nShort note.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nPlan.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "- [Roadmap](/Projects/Roadmap.md)\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("[[PersonalAI Roadmap|Roadmap]]", draft.content)
            self.assertNotIn("[Roadmap](/Projects/Roadmap.md)", draft.content)

    def test_generated_note_cleanup_removes_unsupported_open_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Future\n### Qdrant\nVector database.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nFuture phases.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Future\n"
                    "### Qdrant\n"
                    "Vector database.\n"
                    "\n"
                    "## Open Questions\n"
                    "- How can we leverage Qdrant's capabilities to improve search functionality and knowledge retrieval?\n"
                    "- What are some best practices for implementing the agent runtime in Python?\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("## Open Questions", draft.content)
            self.assertIn("### Qdrant\n\nVector database.", draft.content)

    def test_generated_note_cleanup_removes_h1_open_questions_and_restores_stub_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Future\n### Git\nVersion control.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nFuture phases.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Future\n"
                    "### Git\n"
                    "Version control.\n"
                    "\n"
                    "# Open Questions\n"
                    "- How can Git be used more effectively?\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Git\n\nVersion control.", draft.content)
            self.assertNotIn("# Open Questions", draft.content)

    def test_generated_note_cleanup_removes_grounded_open_questions_from_existing_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Vision.md").write_text(
                "# Vision\n## Goal\nBuild a local AI assistant that can:\n- write code\n- update existing notes\n- refactor knowledge\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nRelated planning note.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Vision\n"
                    "## Goal\n"
                    "Build a local AI assistant that can:\n"
                    "- write code\n"
                    "- update existing notes\n"
                    "- refactor knowledge\n"
                    "\n"
                    "## Open Questions\n"
                    "- How should the assistant prioritize updates?\n"
                ),
                finding_path="Projects/Vision.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("## Open Questions", draft.content)

    def test_generated_note_cleanup_removes_missing_knowledge_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Future\n### Qdrant\nVector database.\n\n### Open WebUI\nUser interface.\n\n### Git\nVersion control.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nFuture phases.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Future\n"
                    "### Qdrant\n"
                    "Vector database.\n"
                    "\n"
                    "### Open WebUI\n"
                    "User interface.\n"
                    "\n"
                    "### Git\n"
                    "Version control.\n"
                    "\n"
                    "## Missing Knowledge\n"
                    "The technology stack could benefit from further exploration of [PersonalAI Roadmap](/Projects/PersonalAI/Roadmap.md).\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("## Missing Knowledge", draft.content)
            self.assertNotIn("[PersonalAI Roadmap](", draft.content)
            self.assertIn("### Qdrant\n\nVector database.", draft.content)

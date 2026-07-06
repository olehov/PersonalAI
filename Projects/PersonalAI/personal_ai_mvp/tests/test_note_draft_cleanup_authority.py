from __future__ import annotations

import tempfile
from pathlib import Path

from tests.note_draft_test_support import NoteDraftServiceTestSupport


class NoteDraftCleanupAuthorityTests(NoteDraftServiceTestSupport):
    def test_generated_note_cleanup_prunes_unsupported_explanatory_clauses(self) -> None:
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
                    "Version control, which is important for collaboration and change tracking.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Git\n\nVersion control", draft.content)
            self.assertNotIn("important for collaboration", draft.content)

    def test_generated_note_cleanup_preserves_authoritative_compact_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Core\n"
                    "### Python\n"
                    "Responsibilities:\n"
                    "- orchestration\n"
                    "- knowledge management\n"
                    "- agent runtime\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("Responsibilities:\n- orchestration\n- knowledge management\n- agent runtime", draft.content)

    def test_generated_note_cleanup_preserves_authoritative_section_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Future\n### Git\nVersion control.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response="# Technology Stack\n## Future\n### Git\nVersion control.\n",
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Git\n\nVersion control.", draft.content)

    def test_generated_note_cleanup_restores_structured_sections_from_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Future\n### Git\nVersion control.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# Technology Stack\n"
                    "## Future\n"
                    "Git is used for version control.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Git\n\nVersion control.", draft.content)
            self.assertNotIn("Git is used for version control.", draft.content)

    def test_generated_note_cleanup_normalizes_house_style_for_authoritative_bullets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n",
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
                    "## Core\n"
                    "### Python\n"
                    "Responsibilities:\n"
                    "- orchestration: coordinates various AI models and services.\n"
                    "- knowledge management: organizes knowledge with NLP and ML tooling.\n"
                    "- agent runtime: executes agents and manages interactions.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("Responsibilities:\n- orchestration\n- knowledge management\n- agent runtime", draft.content)
            self.assertNotIn("coordinates various AI models", draft.content)

    def test_generated_note_cleanup_recollapses_authoritative_bullets_and_prunes_section_intro(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n## Future\n### Git\nVersion control.\n",
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
                    "## Core\n"
                    "### Python\n"
                    "Python is the main implementation layer for the assistant.\n"
                    "Responsibilities:\n"
                    "- orchestration: coordinates various AI models and services.\n"
                    "- knowledge management: organizes knowledge with NLP and ML tooling.\n"
                    "- agent runtime: executes agents and manages interactions.\n"
                    "\n"
                    "## Future\n"
                    "The technology stack will continue to evolve with the addition of new components.\n"
                    "### Git\n"
                    "Version control.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("Responsibilities:\n- orchestration\n- knowledge management\n- agent runtime", draft.content)
            self.assertNotIn("Python is the main implementation layer", draft.content)
            self.assertNotIn("coordinates various AI models", draft.content)
            self.assertNotIn("The technology stack will continue to evolve", draft.content)

    def test_generated_note_cleanup_restores_exact_authoritative_bullet_casing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n",
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
                    "## Core\n"
                    "### Python\n"
                    "Responsibilities:\n"
                    "- Orchestration\n"
                    "- Knowledge management\n"
                    "- Agent runtime\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("Responsibilities:\n- orchestration\n- knowledge management\n- agent runtime", draft.content)
            self.assertNotIn("- Orchestration", draft.content)
            self.assertNotIn("- Knowledge management", draft.content)
            self.assertNotIn("- Agent runtime", draft.content)

    def test_generated_note_cleanup_removes_bridge_prose_between_structured_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\n\nResponsibilities:\n- local LLM inference\n",
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
                    "## Core\n"
                    "### Python\n"
                    "Responsibilities:\n"
                    "- orchestration\n"
                    "- knowledge management\n"
                    "- agent runtime\n"
                    "\n"
                    "The Ollama component handles local LLM inference, while Obsidian provides knowledge storage capabilities.\n"
                    "\n"
                    "### Ollama\n"
                    "Responsibilities:\n"
                    "- local LLM inference\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertNotIn("The Ollama component handles local LLM inference", draft.content)
            self.assertIn("### Ollama", draft.content)
            self.assertIn("- agent runtime\n\n### Ollama", draft.content)

    def test_generated_note_cleanup_preserves_intro_plus_bullets_sections(self) -> None:
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
                    "The assistant should support software engineering workflows across coding and knowledge maintenance.\n"
                    "- write code\n"
                    "- update existing notes\n"
                    "- refactor knowledge\n"
                    "\n"
                    "This should stay concise and practical.\n"
                ),
                finding_path="Projects/Vision.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("## Goal\n\nBuild a local AI assistant that can:\n- write code\n- update existing notes\n- refactor knowledge", draft.content)
            self.assertNotIn("The assistant should support software engineering workflows", draft.content)
            self.assertNotIn("This should stay concise and practical.", draft.content)

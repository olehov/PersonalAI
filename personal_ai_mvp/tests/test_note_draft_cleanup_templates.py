from __future__ import annotations

import tempfile
from pathlib import Path

from tests.note_draft_test_support import NoteDraftServiceTestSupport


class NoteDraftCleanupTemplatesTests(NoteDraftServiceTestSupport):
    def test_generated_note_cleanup_canonicalizes_known_short_sections(self) -> None:
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
                    "A vector database.\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Qdrant\n\nVector database.", draft.content)
            self.assertNotIn("A vector database.", draft.content)

    def test_generated_note_cleanup_restores_missing_authoritative_subsections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\n\nResponsibilities:\n- local LLM inference\n\n### Obsidian\n\nResponsibilities:\n- knowledge storage\n\n## Future\n### Qdrant\nVector database.\n\n### Open WebUI\nUser interface.\n\n### Git\nVersion control.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nFuture phases for vector search and knowledge retrieval.\n",
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
                    "### Ollama\n"
                    "Responsibilities:\n"
                    "- local LLM inference\n"
                    "\n"
                    "### Obsidian\n"
                    "Responsibilities:\n"
                    "- knowledge storage\n"
                    "\n"
                    "## Future\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Qdrant\n\nVector database.", draft.content)
            self.assertIn("### Open WebUI\n\nUser interface.", draft.content)
            self.assertIn("### Git\n\nVersion control.", draft.content)

    def test_generated_note_cleanup_restores_exact_stub_phrase_variants(self) -> None:
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
                    "A vector database\n"
                ),
                finding_path="Projects/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### Qdrant\n\nVector database.", draft.content)
            self.assertNotIn("A vector database", draft.content)

    def test_generated_note_cleanup_restores_numeric_subsection_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "MVP.md").write_text(
                "# MVP\n## Features\n### 1\nRead Vault.\n\n### 2\nBuild embeddings.\n\n### 3\nSemantic search.\n\n### 4\nAnswer questions.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nPhase 1 and Phase 2 planning.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# MVP\n"
                    "## Features\n"
                    "### 1. Read Vault\n"
                    "Read Vault is an essential feature for the AI assistant, allowing it to access and understand Obsidian notes.\n"
                    "\n"
                    "### 2. Build Embeddings\n"
                    "Embeddings are crucial for semantic search and question answering capabilities.\n"
                    "\n"
                    "### 3. Semantic Search\n"
                    "Semantic search helps retrieve notes based on meaning rather than exact keyword matches.\n"
                    "\n"
                    "### 4. Answer Questions\n"
                    "Answer questions turns retrieved knowledge into grounded responses for the user.\n"
                ),
                finding_path="Projects/MVP.md",
                kind="isolated_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### 1\n\nRead Vault.", draft.content)
            self.assertIn("### 2\n\nBuild embeddings.", draft.content)
            self.assertIn("### 3\n\nSemantic search.", draft.content)
            self.assertIn("### 4\n\nAnswer questions.", draft.content)
            self.assertNotIn("essential feature for the AI assistant", draft.content)

    def test_isolated_maintenance_draft_reverts_to_authority_when_numeric_sections_collapse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "MVP.md").write_text(
                "# MVP\n\n## Goal\n\nCreate a local AI assistant capable of:\n\n- reading Obsidian notes\n- searching knowledge\n- answering questions using personal knowledge\n\n## Features\n\n### 1\n\nRead Vault.\n\n### 2\n\nBuild embeddings.\n\n### 3\n\nSemantic search.\n\n### 4\n\nAnswer questions.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Architecture.md").write_text(
                "# PersonalAI Architecture\nHigh-level design.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nFuture phases.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# MVP\n"
                    "## Goal\n"
                    "Create a local AI assistant capable of:\n"
                    "- reading Obsidian notes [[PersonalAI Architecture]]\n"
                    "- searching knowledge\n"
                    "- answering questions using personal knowledge\n"
                    "\n"
                    "## Features\n"
                    "### 1\n"
                    "\n"
                    "### 2\n"
                    "\n"
                    "### 3\n"
                    "\n"
                    "### 4\n"
                    "\n"
                    "Answer questions.\n"
                ),
                finding_path="Projects/MVP.md",
                kind="isolated_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("### 1\n\nRead Vault.", draft.content)
            self.assertIn("### 2\n\nBuild embeddings.", draft.content)
            self.assertIn("### 3\n\nSemantic search.", draft.content)
            self.assertIn("- reading Obsidian notes", draft.content)
            self.assertNotIn("[[PersonalAI Architecture]]", draft.content)

    def test_generated_note_cleanup_restores_stub_sections_even_with_thematic_breaks(self) -> None:
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
                    "Git will be used for version control\n"
                    "\n"
                    "---\n"
                    "\n"
                    "## Open Questions\n"
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
            self.assertNotIn("Git will be used for version control", draft.content)
            self.assertNotIn("## Open Questions", draft.content)

from __future__ import annotations

import tempfile
from pathlib import Path

from personal_ai.application.knowledge_service import serialize_generated_note_draft
from personal_ai.application.maintenance_service import KnowledgeMaintenanceService
from tests.note_draft_test_support import NoteDraftServiceTestSupport


class NoteDraftServiceTests(NoteDraftServiceTestSupport):
    def test_draft_note_generates_content_and_safe_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Binary Search.md").write_text(
                "# Binary Search\nSearch in sorted arrays.\n",
                encoding="utf-8",
            )

            _knowledge, _mutation, fake_client, draft_service = self._build_draft_service(
                root,
                response="# Heap\n- Insert\n- Extract\n",
            )

            draft = draft_service.draft_note(
                title="Heap",
                instruction="Create a short heap note.",
                model="llama3:latest",
                target_dir="Algorithms",
            )
            payload = serialize_generated_note_draft(draft)

            self.assertEqual(payload["model"], "llama3:latest")
            self.assertEqual(payload["proposal"]["action"], "create")
            self.assertEqual(payload["proposal"]["target_path"], "Algorithms/Heap.md")
            self.assertTrue(payload["content"].startswith("# Heap"))
            self.assertEqual(fake_client.calls[0][0], "llama3:latest")

    def test_draft_note_prompt_prefers_technical_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Projects").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nInsert, extract, sift, and complexity details.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "README.md").write_text(
                "# README\nHeap roadmap and project planning.\n",
                encoding="utf-8",
            )

            _knowledge, _mutation, fake_client, draft_service = self._build_draft_service(
                root,
                response="# Heap\n- Insert\n",
            )

            draft_service.draft_note(
                title="Heap",
                instruction="Update the note with heap operations and complexity.",
                model="llama3:latest",
                action="update",
                target_path="Algorithms/Heap.md",
            )

            prompt_text = fake_client.calls[0][1][1].content
            self.assertIn("Algorithms/Heap.md", prompt_text)
            self.assertNotIn("Projects/README.md", prompt_text)

    def test_draft_note_uses_explicit_scope_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Projects").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap operations and complexity.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Heap.md").write_text(
                "# Heap Project\nPlanning notes.\n",
                encoding="utf-8",
            )

            _knowledge, _mutation, fake_client, draft_service = self._build_draft_service(
                root,
                response="# Heap\n- Insert\n",
            )

            draft_service.draft_note(
                title="Heap",
                instruction="Update the heap note.",
                model="llama3:latest",
                action="update",
                target_path="Algorithms/Heap.md",
                scope_dirs=("Algorithms",),
            )

            prompt_text = fake_client.calls[0][1][1].content
            self.assertIn("Algorithms/Heap.md", prompt_text)
            self.assertNotIn("Projects/Heap.md", prompt_text)

    def test_draft_note_prompt_includes_vault_style_guide(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n## Future\n### Git\nVersion control.\n",
                encoding="utf-8",
            )

            _knowledge, _mutation, fake_client, draft_service = self._build_draft_service(
                root,
                response="# Technology Stack\n",
            )

            draft_service.draft_note(
                title="Technology Stack",
                instruction="Refresh the note in the existing house style.",
                model="llama3:latest",
                action="update",
                target_path="Projects/Technology Stack.md",
            )

            prompt_text = fake_client.calls[0][1][1].content
            self.assertIn("Vault Style Guide:", prompt_text)
            self.assertIn("Canonical Examples:", prompt_text)
            self.assertIn("Responsibilities:", prompt_text)
            self.assertIn("Version control.", prompt_text)

    def test_draft_maintenance_finding_generates_refactor_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Vision.md").write_text(
                "# Vision\nShort note.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nRelated planning note with enough detail to avoid sparse planning priority in this test.\nThis roadmap note describes the current project scope, phased delivery expectations, retrieval work, maintenance workflows, and future implementation milestones in enough words.\n[[Vision]]\n",
                encoding="utf-8",
            )

            finding, fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response="# Vision\n## Goal\nExpanded and linked.\n[[Roadmap]]\n",
                finding_path="Projects/Vision.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )
            payload = serialize_generated_note_draft(draft)

            self.assertEqual(payload["proposal"]["action"], "refactor")
            self.assertEqual(payload["proposal"]["target_path"], "Projects/Vision.md")
            self.assertIn("Maintenance refactor", payload["instruction"])
            self.assertEqual(payload["companion_proposals"], [])
            prompt_text = fake_client.calls[0][1][1].content
            self.assertIn("Maintenance finding kind: sparse_note", prompt_text)
            self.assertIn("Current note content:", prompt_text)
            self.assertIn("Do not mention the maintenance process itself inside the note.", prompt_text)
            self.assertIn("Facts to preserve if still correct:", prompt_text)
            self.assertIn("- Short note.", prompt_text)
            self.assertIn("Preferred internal links when relevant:", prompt_text)
            self.assertIn("[[Roadmap]]", prompt_text)
            self.assertIn("Grounded note paths:", prompt_text)
            self.assertIn("Projects/Roadmap.md", prompt_text)
            self.assertIn("Vault Style Guide:", prompt_text)

    def test_draft_maintenance_plan_wraps_single_note_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Vision.md").write_text(
                "# Vision\nShort note.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nRelated planning note.\n[[Vision]]\n",
                encoding="utf-8",
            )

            knowledge, mutation, _fake_client, draft_service = self._build_draft_service(
                root,
                response="# Vision\n## Goal\nExpanded and linked.\n[[Roadmap]]\n",
            )
            maintenance = KnowledgeMaintenanceService(knowledge, mutation)
            plan = maintenance.build_plan(limit=1, kinds=("sparse_note",))

            draft_plan = draft_service.draft_maintenance_plan(
                plan=plan,
                model="llama3:latest",
            )

            self.assertEqual(len(draft_plan.entries), 1)
            self.assertEqual(
                draft_plan.entries[0].draft.proposal.target_path.as_posix(),
                draft_plan.entries[0].plan_entry.proposal.target_path.as_posix(),
            )

    def test_isolated_maintenance_draft_adds_related_links_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI" / "ADR").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "ADR" / "ADR-001-Use-Obsidian.md").write_text(
                "# ADR-001 Use Obsidian\n\nStatus: Accepted\n\n## Context\n\nThe assistant needs a human-readable knowledge base.\n\n## Decision\n\nUse Obsidian as the primary storage.\n\n## Consequences\n\nPositive:\n- Markdown\n- Git friendly\n- Easy editing\n\nNegative:\n- No built-in API\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nRoadmap for the assistant.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Vision.md").write_text(
                "# Personal AI Developer Assistant\nLong-term assistant direction.\n",
                encoding="utf-8",
            )

            finding, _fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response=(
                    "# ADR-001 Use Obsidian\n\nStatus: Accepted\n\nThe assistant needs a human-readable knowledge base [[PersonalAI Roadmap]]. To achieve this, we will use Obsidian as our primary storage [[Personal AI Developer Assistant]].\n\n## Decision\n\nUse Obsidian as the primary storage.\n\n## Consequences\n\nPositive:\n- Markdown\n- Git friendly\n- Easy editing\n\nPositive:\n- No built-in API\n\nOpen Questions:\nWhat are the implications of using Obsidian as our primary storage for our AI assistant's knowledge base?\n"
                ),
                finding_path="Projects/PersonalAI/ADR/ADR-001-Use-Obsidian.md",
                kind="isolated_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            self.assertIn("## Related Notes", draft.content)
            self.assertIn("[[PersonalAI Roadmap]]", draft.content)
            self.assertNotIn("[[ADR-001 Use Obsidian]]", draft.content)
            self.assertIn("## Context", draft.content)
            self.assertIn("## Decision", draft.content)
            self.assertIn("Negative:\n- No built-in API", draft.content)
            self.assertNotIn("Open Questions", draft.content)
            self.assertGreaterEqual(len(draft.companion_proposals), 1)
            companion_paths = {proposal.target_path.as_posix() for proposal in draft.companion_proposals}
            self.assertIn("Projects/PersonalAI/Roadmap.md", companion_paths)
            for proposal in draft.companion_proposals:
                self.assertIn("[[ADR-001 Use Obsidian]]", proposal.proposed_content)

    def test_maintenance_prompt_prefers_sibling_project_notes_over_mvp_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI" / "personal_ai_mvp").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "Technology Stack.md").write_text(
                "# Technology Stack\nShort note.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Roadmap.md").write_text(
                "# Roadmap\nStack evolution and future phases.\n[[Technology Stack]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Vision.md").write_text(
                "# Vision\nLong-term assistant direction.\n[[Technology Stack]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "personal_ai_mvp" / "README.md").write_text(
                "# PersonalAI MVP\nCLI details and implementation notes.\n",
                encoding="utf-8",
            )

            finding, fake_client, draft_service = self._build_maintenance_draft_service(
                root,
                response="# Technology Stack\n## Core\n- Python\n",
                finding_path="Projects/PersonalAI/Technology Stack.md",
                kind="sparse_note",
            )

            draft = draft_service.draft_maintenance_finding(
                finding=finding,
                model="llama3:latest",
            )

            prompt_text = fake_client.calls[0][1][1].content
            self.assertTrue(
                "Projects/PersonalAI/Roadmap.md" in prompt_text
                or "Projects/PersonalAI/Vision.md" in prompt_text
            )
            self.assertNotIn("Projects/PersonalAI/personal_ai_mvp/README.md", prompt_text)
            self.assertNotIn("Projects/PersonalAI/personal_ai_mvp/README.md", draft.citations)
            self.assertTrue(
                "Projects/PersonalAI/Roadmap.md" in draft.citations
                or "Projects/PersonalAI/Vision.md" in draft.citations
            )

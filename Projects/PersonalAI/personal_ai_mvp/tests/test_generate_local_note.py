from __future__ import annotations

import unittest
from pathlib import Path

import generate_local_note
from personal_ai.domain.models import NoteDocument, NoteMetadata, RetrievedNote, RetrievalBundle


class GenerateLocalNoteTests(unittest.TestCase):
    def test_collect_allowed_links_dedupes_and_excludes_current_title(self) -> None:
        bundle = RetrievalBundle(
            question="question",
            primary_notes=(
                RetrievedNote(
                    note=NoteDocument(
                        path=Path("Languages/C/Memory Management in C.md"),
                        title="Memory Management in C",
                        content="# Memory Management in C\n",
                        metadata=NoteMetadata(values={}),
                        links=(),
                    ),
                    score=0.9,
                    reason="primary",
                ),
            ),
            related_notes=(
                RetrievedNote(
                    note=NoteDocument(
                        path=Path("Languages/C/Memory Management in C.md"),
                        title="Memory Management in C",
                        content="# Memory Management in C\n",
                        metadata=NoteMetadata(values={}),
                        links=(),
                    ),
                    score=0.5,
                    reason="related",
                ),
                RetrievedNote(
                    note=NoteDocument(
                        path=Path("Languages/C/File IO in C.md"),
                        title="File IO in C",
                        content="# File IO in C\n",
                        metadata=NoteMetadata(values={}),
                        links=(),
                    ),
                    score=0.4,
                    reason="related",
                ),
            ),
        )

        links = generate_local_note.collect_allowed_links(
            bundle,
            exclude_title="Resource Lifetime and Cleanup in C",
            limit=5,
        )

        self.assertEqual(links, ("Memory Management in C", "File IO in C"))

    def test_build_user_prompt_constrains_links_to_grounded_titles(self) -> None:
        bundle = RetrievalBundle(
            question="question",
            primary_notes=(
                RetrievedNote(
                    note=NoteDocument(
                        path=Path("Languages/C/Undefined Behavior in C.md"),
                        title="Undefined Behavior in C",
                        content="# Undefined Behavior in C\nAvoid UB.\n",
                        metadata=NoteMetadata(values={}),
                        links=(),
                    ),
                    score=0.9,
                    reason="primary",
                ),
            ),
            related_notes=(),
        )

        prompt = generate_local_note.build_user_prompt(
            title="Header Design in C",
            instruction="Explain include guards and stable interfaces.",
            retrieval_bundle=bundle,
            allowed_links=("Undefined Behavior in C",),
        )

        self.assertIn("Only emit internal links from the allowed list below.", prompt)
        self.assertIn("- [[Undefined Behavior in C]]", prompt)
        self.assertIn("Context note paths:", prompt)
        self.assertIn("Languages/C/Undefined Behavior in C.md", prompt)

    def test_strip_code_fences_removes_wrapping_markdown_block(self) -> None:
        stripped = generate_local_note._strip_code_fences(
            "```md\n# C Preprocessor in Practice\n\nBody.\n```\n"
        )

        self.assertEqual(stripped, "# C Preprocessor in Practice\n\nBody.")


if __name__ == "__main__":
    unittest.main()

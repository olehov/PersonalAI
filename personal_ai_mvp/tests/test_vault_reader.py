from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from infrastructure.vault.reader import VaultReader
from tests.path_test_support import runtime_drafts_path


class VaultReaderTests(unittest.TestCase):
    def test_reads_markdown_files_recursively_with_metadata_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "Projects" / "Demo"
            nested.mkdir(parents=True)

            note_path = nested / "Example.md"
            note_path.write_text(
                "---\n"
                "tags:\n"
                "  - python\n"
                "  - obsidian\n"
                "draft: false\n"
                "---\n"
                "# Example Note\n"
                "See [[Other Note]] and [[Folder/Third Note|third]].\n",
                encoding="utf-8",
            )

            other_path = root / "Other Note.md"
            other_path.write_text("# Other Note\n", encoding="utf-8")

            third_dir = root / "Folder"
            third_dir.mkdir()
            (third_dir / "Third Note.md").write_text("# Third Note\n", encoding="utf-8")

            reader = VaultReader(root)
            notes = reader.read_all()

            self.assertEqual(len(notes), 3)
            example = next(note for note in notes if note.path == Path("Projects/Demo/Example.md"))
            self.assertEqual(example.title, "Example Note")
            self.assertEqual(example.metadata.values["tags"], ["python", "obsidian"])
            self.assertFalse(example.metadata.values["draft"])
            self.assertEqual(example.links[0].target, "Other Note")
            self.assertEqual(example.links[1].target, "Folder/Third Note")
            self.assertEqual(example.links[1].alias, "third")

    def test_uses_filename_when_heading_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note_path = root / "Untitled.md"
            note_path.write_text("Plain content.\n", encoding="utf-8")

            note = VaultReader(root).read_note(note_path)

            self.assertEqual(note.title, "Untitled")

    def test_reads_all_when_vault_root_is_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            note_path = root / "Algorithms" / "Binary Search.md"
            note_path.parent.mkdir(parents=True)
            note_path.write_text("# Binary Search\nSearch sorted arrays.\n", encoding="utf-8")

            current_dir = Path.cwd()
            try:
                relative_root = root.relative_to(current_dir)
            except ValueError:
                self.skipTest("Temporary directory is not relative to the current working directory.")

            reader = VaultReader(relative_root)
            notes = reader.read_all()

            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0].path, Path("Algorithms/Binary Search.md"))
            self.assertEqual(notes[0].title, "Binary Search")

    def test_skips_restricted_markdown_areas_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Knowledge").mkdir()
            (root / "Knowledge" / "Visible.md").write_text("# Visible\n", encoding="utf-8")
            (root / ".history" / "20260622" / "Knowledge").mkdir(parents=True)
            (root / ".history" / "20260622" / "Knowledge" / "Backup.md").write_text(
                "# Backup\n",
                encoding="utf-8",
            )
            runtime_drafts_path(root).mkdir(parents=True)
            (runtime_drafts_path(root) / "Draft.md").write_text(
                "# Draft\n",
                encoding="utf-8",
            )
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "Config.md").write_text("# Config\n", encoding="utf-8")

            notes = VaultReader(root).read_all()

            self.assertEqual([note.path.as_posix() for note in notes], ["Knowledge/Visible.md"])

    def test_skips_non_utf8_markdown_files_during_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Knowledge").mkdir()
            (root / "Knowledge" / "Visible.md").write_text("# Visible\n", encoding="utf-8")
            (root / "Knowledge" / "Broken.md").write_bytes(b"# Broken\n\xc3\x28\n")

            seen_errors: list[str] = []
            reader = VaultReader(
                root,
                on_read_error=lambda path, _exc: seen_errors.append(path.name),
            )

            notes = reader.read_all()

            self.assertEqual([note.path.as_posix() for note in notes], ["Knowledge/Visible.md"])
            self.assertEqual(seen_errors, ["Broken.md"])


if __name__ == "__main__":
    unittest.main()

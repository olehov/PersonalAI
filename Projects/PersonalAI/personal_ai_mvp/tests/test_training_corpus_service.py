from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.training_corpus_service import TrainingCorpusService


class TrainingCorpusServiceTests(unittest.TestCase):
    def test_build_corpus_generates_rewrite_and_outline_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n## Future\n### Git\nVersion control.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            corpus = TrainingCorpusService(knowledge).build_corpus(limit=5, source="synthetic")

            self.assertGreaterEqual(len(corpus.examples), 2)
            tasks = {example.task for example in corpus.examples}
            self.assertIn("rewrite_note_to_house_style", tasks)
            self.assertIn("expand_outline_to_note", tasks)

            rewrite = next(
                example for example in corpus.examples
                if example.task == "rewrite_note_to_house_style"
            )
            self.assertIn("## Missing Knowledge", rewrite.input_markdown)
            self.assertIn("Key responsibilities:", rewrite.input_markdown)
            self.assertIn("Responsibilities:", rewrite.target_markdown)
            self.assertIn("responsibilities", rewrite.tags)

    def test_build_corpus_skips_tiny_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Tiny.md").write_text(
                "# Tiny\nShort.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            corpus = TrainingCorpusService(knowledge).build_corpus(limit=5, source="synthetic")

            self.assertEqual(corpus.examples, ())

    def test_build_corpus_can_load_curated_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            curated_dir = root / "curated"
            curated_dir.mkdir()
            (curated_dir / "example.json").write_text(
                json.dumps(
                    {
                        "example_id": "curated::example",
                        "task": "rewrite_note_to_house_style",
                        "source_note_path": "Projects/Example.md",
                        "title": "Example",
                        "instruction": "Rewrite the note.",
                        "input_markdown": "# Example\nBad.\n",
                        "target_markdown": "# Example\n\nGood.\n",
                        "tags": ["curated", "projects"],
                    }
                ),
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            corpus = TrainingCorpusService(
                knowledge,
                curated_examples_dir=curated_dir,
            ).build_corpus(limit=5, source="curated")

            self.assertEqual(len(corpus.examples), 1)
            self.assertEqual(corpus.examples[0].example_id, "curated::example")
            self.assertEqual(corpus.examples[0].source, "curated")
            self.assertEqual(corpus.examples[0].quality_tier, "gold")
            self.assertEqual(corpus.examples[0].tags[0], "curated")

    def test_build_corpus_can_load_ukrainian_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ukrainian_dir = root / "ukrainian"
            ukrainian_dir.mkdir()
            (ukrainian_dir / "example.json").write_text(
                json.dumps(
                    {
                        "example_id": "ukrainian::example",
                        "task": "ukrainian_grammar_cleanup",
                        "source_note_path": "Inbox/Ukrainian Draft.md",
                        "title": "Example",
                        "instruction": "Виправ граматику.",
                        "input_markdown": "# Example\nТут є ошибка.\n",
                        "target_markdown": "# Example\n\nТут є помилка.\n",
                        "tags": ["ukrainian", "grammar"],
                    }
                ),
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            corpus = TrainingCorpusService(
                knowledge,
                ukrainian_examples_dir=ukrainian_dir,
            ).build_corpus(limit=5, source="ukrainian")

            self.assertEqual(len(corpus.examples), 1)
            self.assertEqual(corpus.examples[0].example_id, "ukrainian::example")
            self.assertEqual(corpus.examples[0].source, "ukrainian")
            self.assertEqual(corpus.examples[0].tags[0], "ukrainian")

    def test_build_manifest_summarizes_sources_and_quality(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            curated_dir = root / "curated"
            ukrainian_dir = root / "ukrainian"
            curated_dir.mkdir()
            ukrainian_dir.mkdir()
            (curated_dir / "example.json").write_text(
                json.dumps(
                    {
                        "example_id": "curated::example",
                        "source": "curated",
                        "quality_tier": "gold",
                        "task": "rewrite_note_to_house_style",
                        "source_note_path": "Projects/Example.md",
                        "title": "Example",
                        "instruction": "Rewrite the note.",
                        "input_markdown": "# Example\nBad.\n",
                        "target_markdown": "# Example\n\nGood.\n",
                        "tags": ["curated", "projects"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\nResponsibilities:\n- local LLM inference\n- retrieval orchestration\n- grounded answer generation\n- safe note drafting\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = TrainingCorpusService(
                knowledge,
                curated_examples_dir=curated_dir,
                ukrainian_examples_dir=ukrainian_dir,
            )
            manifest = service.build_manifest(limit=5, source="all")

            self.assertGreaterEqual(manifest.total_examples, 2)
            self.assertEqual(manifest.by_source["curated"], 1)
            self.assertGreaterEqual(manifest.by_source["synthetic"], 1)
            self.assertEqual(manifest.by_quality_tier["gold"], 1)
            self.assertGreaterEqual(manifest.by_quality_tier["silver"], 1)

    def test_build_split_favors_curated_gold_for_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            curated_dir = root / "curated"
            ukrainian_dir = root / "ukrainian"
            curated_dir.mkdir()
            ukrainian_dir.mkdir()
            (curated_dir / "example.json").write_text(
                json.dumps(
                    {
                        "example_id": "curated::example",
                        "source": "curated",
                        "quality_tier": "gold",
                        "task": "rewrite_note_to_house_style",
                        "source_note_path": "Projects/Example.md",
                        "title": "Example",
                        "instruction": "Rewrite the note.",
                        "input_markdown": "# Example\nBad.\n",
                        "target_markdown": "# Example\n\nGood.\n",
                        "tags": ["curated", "projects"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\nResponsibilities:\n- local LLM inference\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = TrainingCorpusService(
                knowledge,
                curated_examples_dir=curated_dir,
                ukrainian_examples_dir=ukrainian_dir,
            )
            split = service.build_split(limit=5, source="all", validation_ratio=0.4)

            self.assertTrue(split.policy.startswith("Deterministic split"))
            validation_ids = {example.example_id for example in split.validation_examples}
            self.assertIn("curated::example", validation_ids)
            self.assertGreaterEqual(len(split.train_examples), 1)

    def test_build_split_fills_validation_target_when_only_curated_gold_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            curated_dir = root / "curated"
            curated_dir.mkdir()
            for index in range(5):
                (curated_dir / f"example_{index}.json").write_text(
                    json.dumps(
                        {
                            "example_id": f"curated::example::{index}",
                            "source": "curated",
                            "quality_tier": "gold",
                            "task": "rewrite_note_to_house_style",
                            "source_note_path": f"Projects/Example {index}.md",
                            "title": f"Example {index}",
                            "instruction": "Rewrite the note.",
                            "input_markdown": f"# Example {index}\nBad.\n",
                            "target_markdown": f"# Example {index}\n\nGood.\n",
                            "tags": ["curated", "projects"],
                        }
                    ),
                    encoding="utf-8",
                )

            knowledge = KnowledgeService(root)
            knowledge.load()
            service = TrainingCorpusService(
                knowledge,
                curated_examples_dir=curated_dir,
            )
            split = service.build_split(limit=10, source="curated", validation_ratio=0.4)

            self.assertEqual(len(split.validation_examples), 2)
            self.assertEqual(len(split.train_examples), 3)


if __name__ == "__main__":
    unittest.main()

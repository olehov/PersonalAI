from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from application.knowledge.knowledge_service import KnowledgeService
from application.training.corpus_service import TrainingCorpusService
from application.training.fine_tune_service import TrainingFineTuneService


class TrainingFineTuneServiceTests(unittest.TestCase):
    def test_build_bundle_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            curated_dir = root / "curated"
            curated_dir.mkdir()
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

            knowledge = KnowledgeService(root)
            knowledge.load()
            corpus_service = TrainingCorpusService(
                knowledge,
                curated_examples_dir=curated_dir,
            )
            fine_tune_service = TrainingFineTuneService(corpus_service)

            bundle = fine_tune_service.build_bundle(
                output_dir=root / "bundle_out",
                limit=5,
                source="curated",
                validation_ratio=0.4,
                model_family="llama",
            )

            self.assertTrue(bundle.train_path.exists())
            self.assertTrue(bundle.validation_path.exists())
            self.assertTrue(bundle.manifest_path.exists())
            self.assertTrue(bundle.recipe_path.exists())
            self.assertTrue(bundle.runbook_path.exists())
            self.assertIn("llama_curated", bundle.bundle_dir.as_posix())
            self.assertEqual(len(bundle.trainer_artifacts), 4)
            self.assertEqual(
                len([artifact for artifact in bundle.trainer_artifacts if artifact.kind == "config"]),
                2,
            )
            self.assertEqual(
                len([artifact for artifact in bundle.trainer_artifacts if artifact.kind == "launch_script"]),
                2,
            )

            manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["source"], "curated")
            self.assertEqual(manifest["recipe"]["model_family"], "llama")
            self.assertIn("unsloth:config", manifest["files"]["trainer_artifacts"])
            self.assertIn("llamafactory:config", manifest["files"]["trainer_artifacts"])
            self.assertIn("unsloth:launch_script", manifest["files"]["trainer_artifacts"])
            self.assertIn("llamafactory:launch_script", manifest["files"]["trainer_artifacts"])

            recipe = json.loads(bundle.recipe_path.read_text(encoding="utf-8"))
            self.assertEqual(recipe["dataset_format"], "jsonl_chat")
            self.assertEqual(recipe["recommended_framework"], "lora")

            train_text = bundle.train_path.read_text(encoding="utf-8")
            validation_text = bundle.validation_path.read_text(encoding="utf-8")
            self.assertIn('"messages"', train_text + validation_text)
            runbook_text = bundle.runbook_path.read_text(encoding="utf-8")
            self.assertIn("Fine-Tune Runbook", runbook_text)
            self.assertIn("unsloth_config.json", runbook_text)
            self.assertIn("llamafactory_config.json", runbook_text)

            unsloth_path = next(
                artifact.path for artifact in bundle.trainer_artifacts
                if artifact.trainer == "unsloth" and artifact.kind == "config"
            )
            llamafactory_path = next(
                artifact.path for artifact in bundle.trainer_artifacts
                if artifact.trainer == "llamafactory" and artifact.kind == "config"
            )
            unsloth_launch_path = next(
                artifact.path for artifact in bundle.trainer_artifacts
                if artifact.trainer == "unsloth" and artifact.kind == "launch_script"
            )
            unsloth_payload = json.loads(unsloth_path.read_text(encoding="utf-8"))
            llamafactory_payload = json.loads(llamafactory_path.read_text(encoding="utf-8"))
            self.assertEqual(unsloth_payload["trainer"], "unsloth")
            self.assertEqual(llamafactory_payload["trainer"], "llamafactory")
            launch_text = unsloth_launch_path.read_text(encoding="utf-8")
            self.assertIn("train_unsloth.py", launch_text)
            self.assertIn(".venv-unsloth\\Scripts\\python.exe", launch_text)


if __name__ == "__main__":
    unittest.main()

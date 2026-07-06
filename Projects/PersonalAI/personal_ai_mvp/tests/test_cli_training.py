from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from personal_ai.domain.models import (
    TrainingEvaluationComparison,
    TrainingEvaluationLeaderboard,
    TrainingEvaluationLeaderboardEntry,
    TrainingFineTuneBundle,
    TrainingFineTuneRecipe,
    TrainingOptimizerLeaderboard,
    TrainingOptimizerLeaderboardEntry,
    TrainingOptimizerSweepReport,
    TrainingTrainerArtifact,
)
from tests.cli_test_support import CliTestSupport


class TrainingCliTests(CliTestSupport):
    def test_training_corpus_outputs_json_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\nResponsibilities:\n- local LLM inference\n",
                encoding="utf-8",
            )

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "training-corpus",
                    "--limit",
                    "5",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertGreaterEqual(len(payload["examples"]), 1)
            self.assertEqual(payload["examples"][0]["task"], "rewrite_note_to_house_style")
            self.assertIn("source", payload["examples"][0])
            self.assertIn("quality_tier", payload["examples"][0])

    def test_training_corpus_outputs_chat_jsonl_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Technology Stack.md").write_text(
                "# Technology Stack\n## Core\n### Python\nResponsibilities:\n- orchestration\n- knowledge management\n- agent runtime\n\n### Ollama\nResponsibilities:\n- local LLM inference\n",
                encoding="utf-8",
            )

            exit_code, stdout = self._run_cli(
                [
                    "--vault",
                    str(root),
                    "training-corpus",
                    "--limit",
                    "2",
                    "--dataset-format",
                    "jsonl_chat",
                ]
            )

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertGreaterEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["messages"][0]["role"], "system")
            self.assertEqual(record["messages"][1]["role"], "user")
            self.assertEqual(record["messages"][2]["role"], "assistant")
            self.assertIn("example_id", record["metadata"])

    def test_training_corpus_outputs_curated_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "training-corpus",
                    "--limit",
                    "3",
                    "--source",
                    "curated",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertGreaterEqual(len(payload["examples"]), 1)
            self.assertTrue(payload["examples"][0]["example_id"].startswith("curated::"))

    def test_training_manifest_outputs_json_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "training-manifest",
                    "--limit",
                    "5",
                    "--source",
                    "curated",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("total_examples", payload)
            self.assertIn("by_source", payload)
            self.assertIn("by_quality_tier", payload)
            self.assertEqual(payload["by_source"]["curated"], payload["total_examples"])

    def test_training_split_outputs_validation_chat_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            exit_code, stdout = self._run_cli(
                [
                    "--vault",
                    str(root),
                    "training-split",
                    "--limit",
                    "3",
                    "--source",
                    "curated",
                    "--validation-ratio",
                    "0.5",
                    "--dataset-format",
                    "jsonl_chat",
                    "--subset",
                    "validation",
                ]
            )

            self.assertEqual(exit_code, 0)
            lines = [line for line in stdout.splitlines() if line.strip()]
            self.assertGreaterEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["messages"][0]["role"], "system")
            self.assertTrue(record["metadata"]["example_id"].startswith("curated::"))

    def test_training_eval_outputs_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.build_prompt_patch_plan",
                return_value=self._prompt_patch_plan(),
            ), patch(
                "personal_ai.cli.TrainingEvalService.evaluate",
                return_value=self._training_report(
                    average_score=0.875,
                    exact_match_rate=0.5,
                    results=(self._training_result(),),
                    failure_snapshots=(self._training_failure_snapshot(),),
                    prompt_patch_suggestions=(
                        self._prompt_patch_suggestion(
                            error_tag="style_drift",
                            instruction="Use plain Obsidian markdown house style.",
                            rationale="Decorative formatting drifted from house style.",
                        ),
                    ),
                ),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-eval",
                        "--limit",
                        "3",
                        "--source",
                        "curated",
                        "--model",
                        "llama3:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["model"], "llama3:latest")
            self.assertEqual(payload["subset"], "validation")
            self.assertEqual(payload["average_score"], 0.875)
            self.assertEqual(payload["results"][0]["example_id"], "curated::example")
            self.assertEqual(payload["failure_snapshots"][0]["example_id"], "curated::example")
            self.assertEqual(payload["failure_snapshots"][0]["error_tags"], ["style_drift"])
            self.assertEqual(payload["prompt_patch_suggestions"][0]["error_tag"], "style_drift")

    def test_training_eval_can_apply_history_patches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.build_prompt_patch_plan",
                return_value=self._prompt_patch_plan(
                    optimized_system_prompt="base\n- Start directly with note content.",
                    suggestions=(
                        self._prompt_patch_suggestion(
                            error_tag="meta_preface",
                            occurrences=2,
                            instruction="Start directly with note content.",
                            rationale="Remove assistant framing.",
                        ),
                    ),
                ),
            ), patch(
                "personal_ai.cli.TrainingEvalService.evaluate",
                return_value=self._training_report(average_score=0.5),
            ) as evaluate_mock:
                exit_code, _payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-eval",
                        "--limit",
                        "3",
                        "--source",
                        "curated",
                        "--model",
                        "llama3:latest",
                        "--apply-history-patches",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                evaluate_mock.call_args.kwargs["extra_instructions"],
                ("Start directly with note content.",),
            )

    def test_training_leaderboard_outputs_json_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.build_leaderboard",
                return_value=TrainingEvaluationLeaderboard(
                    total_runs=2,
                    entries=(
                        TrainingEvaluationLeaderboardEntry(
                            model="llama3:latest",
                            subset="validation",
                            runs=2,
                            average_score=0.5,
                            best_score=0.6,
                            latest_score=0.55,
                            delta_vs_previous_score=0.1,
                            delta_vs_best_score=-0.05,
                            average_exact_match_rate=0.25,
                            latest_exact_match_rate=0.5,
                            delta_vs_previous_exact_match_rate=0.25,
                            delta_vs_best_exact_match_rate=0.0,
                            last_evaluated_at=self._now(),
                            latest_failure_snapshots=(
                                self._training_failure_snapshot(
                                    score=0.55,
                                    error_tags=("style_drift", "missing_links"),
                                ),
                            ),
                            prompt_patch_suggestions=(
                                self._prompt_patch_suggestion(
                                    error_tag="missing_links",
                                    instruction="Keep all grounded internal [[Note Title]] links.",
                                    rationale="The model is dropping graph connections.",
                                ),
                            ),
                        ),
                    ),
                ),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-leaderboard",
                        "--subset",
                        "validation",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["total_runs"], 2)
            self.assertEqual(payload["entries"][0]["model"], "llama3:latest")
            self.assertEqual(payload["entries"][0]["runs"], 2)
            self.assertEqual(payload["entries"][0]["delta_vs_previous_score"], 0.1)
            self.assertEqual(payload["entries"][0]["delta_vs_best_score"], -0.05)
            self.assertEqual(
                payload["entries"][0]["latest_failure_snapshots"][0]["example_id"],
                "curated::example",
            )
            self.assertEqual(
                payload["entries"][0]["latest_failure_snapshots"][0]["error_tags"],
                ["style_drift", "missing_links"],
            )
            self.assertEqual(
                payload["entries"][0]["prompt_patch_suggestions"][0]["error_tag"],
                "missing_links",
            )

    def test_training_prompt_patches_outputs_json_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.build_prompt_patch_plan",
                return_value=self._prompt_patch_plan(
                    base_system_prompt="base prompt",
                    optimized_system_prompt="base prompt\n\nAdditional Focus Instructions:\n- Preserve heading hierarchy.",
                    suggestions=(
                        self._prompt_patch_suggestion(
                            error_tag="missing_headings",
                            occurrences=2,
                            instruction="Preserve heading hierarchy.",
                            rationale="Keep expected sections.",
                        ),
                    ),
                ),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-prompt-patches",
                        "--subset",
                        "validation",
                        "--model",
                        "llama3:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["suggestions"][0]["error_tag"], "missing_headings")
            self.assertIn("Additional Focus Instructions:", payload["optimized_system_prompt"])

    def test_training_eval_compare_outputs_json_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            baseline_report = self._training_report(average_score=0.3)
            optimized_report = self._training_report(average_score=0.45, exact_match_rate=0.25)
            prompt_plan = self._prompt_patch_plan(
                optimized_system_prompt="base\n\nAdditional Focus Instructions:\n- Preserve heading hierarchy.",
                suggestions=(
                    self._prompt_patch_suggestion(
                        error_tag="missing_headings",
                        occurrences=2,
                        instruction="Preserve heading hierarchy.",
                        rationale="Keep expected sections.",
                    ),
                ),
            )

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.build_prompt_patch_plan",
                return_value=prompt_plan,
            ), patch(
                "personal_ai.cli.TrainingEvalService.evaluate",
                side_effect=[baseline_report, optimized_report],
            ), patch(
                "personal_ai.cli.TrainingEvalService.compare_reports",
                return_value=TrainingEvaluationComparison(
                    model="llama3:latest",
                    subset="validation",
                    baseline_report=baseline_report,
                    optimized_report=optimized_report,
                    optimized_prompt_plan=prompt_plan,
                    score_delta=0.15,
                    exact_match_rate_delta=0.25,
                ),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-eval-compare",
                        "--limit",
                        "3",
                        "--source",
                        "curated",
                        "--model",
                        "llama3:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["score_delta"], 0.15)
            self.assertEqual(payload["exact_match_rate_delta"], 0.25)
            self.assertEqual(payload["optimized_report"]["average_score"], 0.45)

    def test_training_optimizer_leaderboard_outputs_json_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with patch(
                "personal_ai.cli.TrainingEvalService.load_comparison_history",
                return_value=(),
            ), patch(
                "personal_ai.cli.TrainingEvalService.build_optimizer_leaderboard",
                return_value=TrainingOptimizerLeaderboard(
                    total_runs=2,
                    entries=(
                        TrainingOptimizerLeaderboardEntry(
                            model="llama3:latest",
                            subset="validation",
                            runs=2,
                            average_score_delta=0.12,
                            best_score_delta=0.15,
                            latest_score_delta=0.1,
                            average_exact_match_rate_delta=0.0,
                            latest_exact_match_rate_delta=0.0,
                            last_evaluated_at=self._now(),
                        ),
                    ),
                ),
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-optimizer-leaderboard",
                        "--subset",
                        "validation",
                        "--model",
                        "llama3:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["total_runs"], 2)
            self.assertEqual(payload["entries"][0]["model"], "llama3:latest")
            self.assertEqual(payload["entries"][0]["average_score_delta"], 0.12)

    def test_training_optimizer_sweep_outputs_json_comparisons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            baseline_report = self._training_report(average_score=0.3)
            optimized_report = self._training_report(average_score=0.45)
            prompt_plan = self._prompt_patch_plan(
                optimized_system_prompt="base\n\nAdditional Focus Instructions:\n- Preserve heading hierarchy.",
                suggestions=(
                    self._prompt_patch_suggestion(
                        error_tag="missing_headings",
                        occurrences=2,
                        instruction="Preserve heading hierarchy.",
                        rationale="Keep expected sections.",
                    ),
                ),
            )
            sweep_report = TrainingOptimizerSweepReport(
                subset="validation",
                comparisons=(
                    TrainingEvaluationComparison(
                        model="llama3:latest",
                        subset="validation",
                        baseline_report=baseline_report,
                        optimized_report=optimized_report,
                        optimized_prompt_plan=prompt_plan,
                        score_delta=0.15,
                        exact_match_rate_delta=0.0,
                    ),
                ),
            )

            with patch("personal_ai.cli.TrainingEvalService.load_history", return_value=()), patch(
                "personal_ai.cli.TrainingEvalService.run_optimizer_sweep",
                return_value=sweep_report,
            ), patch(
                "personal_ai.cli.TrainingEvalService.append_comparison",
                return_value=None,
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-optimizer-sweep",
                        "--limit",
                        "3",
                        "--source",
                        "curated",
                        "--model",
                        "llama3:latest",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["subset"], "validation")
            self.assertEqual(payload["comparisons"][0]["model"], "llama3:latest")
            self.assertEqual(payload["comparisons"][0]["score_delta"], 0.15)

    def test_training_bundle_outputs_json_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle_dir = root / "fine_tune" / "llama_curated"
            recipe = TrainingFineTuneRecipe(
                model_family="llama",
                dataset_format="jsonl_chat",
                recommended_framework="lora",
                learning_rate=2e-4,
                num_epochs=3,
                micro_batch_size=2,
                gradient_accumulation_steps=8,
                lora_rank=16,
                lora_alpha=32,
                lora_dropout=0.05,
                max_sequence_length=4096,
                notes=("Start with a dry run.",),
            )
            bundle = TrainingFineTuneBundle(
                bundle_dir=bundle_dir,
                train_path=bundle_dir / "train.jsonl",
                validation_path=bundle_dir / "validation.jsonl",
                manifest_path=bundle_dir / "manifest.json",
                recipe_path=bundle_dir / "recipe.json",
                runbook_path=bundle_dir / "RUNBOOK.md",
                trainer_artifacts=(
                    TrainingTrainerArtifact(
                        trainer="unsloth",
                        kind="config",
                        path=bundle_dir / "unsloth_config.json",
                        format="json",
                    ),
                    TrainingTrainerArtifact(
                        trainer="llamafactory",
                        kind="config",
                        path=bundle_dir / "llamafactory_config.json",
                        format="json",
                    ),
                    TrainingTrainerArtifact(
                        trainer="unsloth",
                        kind="launch_script",
                        path=bundle_dir / "launch_unsloth.ps1",
                        format="powershell",
                    ),
                    TrainingTrainerArtifact(
                        trainer="llamafactory",
                        kind="launch_script",
                        path=bundle_dir / "launch_llamafactory.ps1",
                        format="powershell",
                    ),
                ),
                source="curated",
                validation_ratio=0.2,
                train_examples=10,
                validation_examples=2,
                recipe=recipe,
            )

            with patch(
                "personal_ai.cli.TrainingFineTuneService.build_bundle",
                return_value=bundle,
            ):
                exit_code, payload = self._run_cli_json(
                    [
                        "--vault",
                        str(root),
                        "--format",
                        "json",
                        "training-bundle",
                        "--source",
                        "curated",
                        "--model-family",
                        "llama",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["source"], "curated")
            self.assertEqual(payload["recipe"]["model_family"], "llama")
            self.assertTrue(payload["train_path"].endswith("train.jsonl"))
            self.assertEqual(payload["trainer_artifacts"][0]["trainer"], "unsloth")
            self.assertEqual(payload["trainer_artifacts"][0]["kind"], "config")

    def test_training_corpus_accepts_ukrainian_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            exit_code, payload = self._run_cli_json(
                [
                    "--vault",
                    str(root),
                    "--format",
                    "json",
                    "training-corpus",
                    "--limit",
                    "2",
                    "--source",
                    "ukrainian",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("examples", payload)

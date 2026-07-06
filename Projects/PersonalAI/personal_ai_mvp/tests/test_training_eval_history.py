from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from tests.training_eval_test_support import TrainingEvalServiceTestSupport


class TrainingEvalHistoryTests(TrainingEvalServiceTestSupport):
    def test_append_and_load_history_round_trip(self) -> None:
        service = self._build_empty_service()
        report = self._report(average_score=0.75, exact_match_rate=0.25)

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "eval_history.jsonl"
            service.append_report(report=report, history_path=history_path)
            loaded = service.load_history(history_path=history_path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].model, "llama3:latest")
        self.assertEqual(loaded[0].subset, "validation")
        self.assertEqual(loaded[0].average_score, 0.75)
        self.assertEqual(loaded[0].failure_snapshots, ())
        self.assertEqual(loaded[0].prompt_patch_suggestions, ())

    def test_build_leaderboard_aggregates_history_by_model_and_subset(self) -> None:
        service = self._build_empty_service()
        reports = (
            self._report(
                average_score=0.4,
                generated_at=datetime(2026, 6, 7, 10, 0, tzinfo=UTC),
            ),
            self._report(
                average_score=0.6,
                exact_match_rate=0.5,
                generated_at=datetime(2026, 6, 7, 11, 0, tzinfo=UTC),
            ),
            self._report(
                model="mistral:latest",
                average_score=0.8,
                exact_match_rate=0.25,
                generated_at=datetime(2026, 6, 7, 9, 0, tzinfo=UTC),
            ),
        )

        leaderboard = service.build_leaderboard(reports=reports, subset="validation")

        self.assertEqual(leaderboard.total_runs, 3)
        self.assertEqual(len(leaderboard.entries), 2)
        self.assertEqual(leaderboard.entries[0].model, "mistral:latest")
        self.assertEqual(leaderboard.entries[0].latest_score, 0.8)
        llama_entry = next(
            entry for entry in leaderboard.entries
            if entry.model == "llama3:latest"
        )
        self.assertEqual(llama_entry.runs, 2)
        self.assertEqual(llama_entry.average_score, 0.5)
        self.assertEqual(llama_entry.best_score, 0.6)
        self.assertEqual(llama_entry.delta_vs_previous_score, 0.2)
        self.assertEqual(llama_entry.delta_vs_best_score, 0.0)
        self.assertEqual(llama_entry.latest_exact_match_rate, 0.5)
        self.assertEqual(llama_entry.delta_vs_previous_exact_match_rate, 0.5)
        self.assertEqual(llama_entry.delta_vs_best_exact_match_rate, 0.0)
        self.assertEqual(llama_entry.latest_failure_snapshots, ())
        self.assertEqual(llama_entry.prompt_patch_suggestions, ())

    def test_build_prompt_patch_plan_aggregates_suggestions_from_history(self) -> None:
        service = self._build_empty_service()
        reports = (
            self._report(
                average_score=0.3,
                prompt_patch_suggestions=(
                    self._suggestion(
                        error_tag="meta_preface",
                        instruction="Start directly with note content.",
                        rationale="Remove assistant framing.",
                    ),
                ),
                generated_at=datetime(2026, 6, 7, 10, 0, tzinfo=UTC),
            ),
            self._report(
                average_score=0.4,
                prompt_patch_suggestions=(
                    self._suggestion(
                        error_tag="meta_preface",
                        instruction="Start directly with note content.",
                        rationale="Remove assistant framing.",
                    ),
                    self._suggestion(
                        error_tag="missing_headings",
                        instruction="Preserve heading hierarchy.",
                        rationale="Keep expected sections.",
                    ),
                ),
                generated_at=datetime(2026, 6, 7, 11, 0, tzinfo=UTC),
            ),
        )

        plan = service.build_prompt_patch_plan(
            reports=reports,
            subset="validation",
            model="llama3:latest",
            limit=5,
        )

        self.assertEqual(plan.suggestions[0].error_tag, "meta_preface")
        self.assertEqual(plan.suggestions[0].occurrences, 2)
        self.assertIn("Start directly with note content.", plan.optimized_system_prompt)
        self.assertIn("Preserve heading hierarchy.", plan.optimized_system_prompt)

    def test_build_prompt_patch_plan_falls_back_to_subset_history_for_new_model(self) -> None:
        service = self._build_empty_service()
        reports = (
            self._report(
                average_score=0.3,
                prompt_patch_suggestions=(
                    self._suggestion(
                        error_tag="missing_headings",
                        occurrences=2,
                        instruction="Preserve heading hierarchy.",
                        rationale="Keep expected sections.",
                    ),
                ),
            ),
        )

        plan = service.build_prompt_patch_plan(
            reports=reports,
            subset="validation",
            model="qwen2.5:7b",
            limit=5,
        )

        suggestion_tags = {suggestion.error_tag for suggestion in plan.suggestions}
        self.assertIn("missing_headings", suggestion_tags)
        self.assertIn("model_profile_qwen_links", suggestion_tags)
        self.assertIn("Use internal links strictly as [[Note Title]]", plan.optimized_system_prompt)

    def test_build_prompt_patch_plan_adds_model_specific_profiles(self) -> None:
        service = self._build_empty_service()

        qwen_plan = service.build_prompt_patch_plan(
            reports=(),
            subset="validation",
            model="qwen2.5:7b",
            limit=5,
        )
        mistral_plan = service.build_prompt_patch_plan(
            reports=(),
            subset="validation",
            model="mistral:7b",
            limit=5,
        )
        llama_plan = service.build_prompt_patch_plan(
            reports=(),
            subset="validation",
            model="llama3:latest",
            limit=5,
        )

        self.assertTrue(
            any(s.error_tag == "model_profile_qwen_links" for s in qwen_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_qwen_link_lines" for s in qwen_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_qwen_no_alias_drift" for s in qwen_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_mistral_no_fences" for s in mistral_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_mistral_keep_bullets" for s in mistral_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_mistral_low_paraphrase" for s in mistral_plan.suggestions)
        )
        self.assertTrue(
            any(s.error_tag == "model_profile_llama_no_preface" for s in llama_plan.suggestions)
        )

    def test_compare_reports_returns_score_deltas(self) -> None:
        service = self._build_empty_service()
        baseline = self._report(average_score=0.3)
        optimized = self._report(average_score=0.45, exact_match_rate=0.25)
        plan = service.build_prompt_patch_plan(reports=(), subset="validation", model="llama3:latest")

        comparison = service.compare_reports(
            model="llama3:latest",
            subset="validation",
            baseline_report=baseline,
            optimized_report=optimized,
            optimized_prompt_plan=plan,
        )

        self.assertEqual(comparison.score_delta, 0.15)
        self.assertEqual(comparison.exact_match_rate_delta, 0.25)
        self.assertEqual(comparison.optimized_prompt_plan.optimized_system_prompt, plan.optimized_system_prompt)

    def test_append_and_load_comparison_history_round_trip(self) -> None:
        service = self._build_empty_service()
        report = self._report(average_score=0.3)
        plan = service.build_prompt_patch_plan(reports=(), subset="validation", model="llama3:latest")
        comparison = service.compare_reports(
            model="llama3:latest",
            subset="validation",
            baseline_report=report,
            optimized_report=report,
            optimized_prompt_plan=plan,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "compare_history.jsonl"
            service.append_comparison(comparison=comparison, history_path=history_path)
            loaded = service.load_comparison_history(history_path=history_path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].model, "llama3:latest")
        self.assertEqual(loaded[0].score_delta, 0.0)

    def test_build_optimizer_leaderboard_aggregates_compare_history(self) -> None:
        service = self._build_empty_service()
        report = self._report(average_score=0.3)
        plan = service.build_prompt_patch_plan(reports=(), subset="validation", model="llama3:latest")
        comparisons = (
            service.compare_reports(
                model="llama3:latest",
                subset="validation",
                baseline_report=report,
                optimized_report=self._report(
                    average_score=0.4,
                    generated_at=datetime(2026, 6, 7, 10, 0, tzinfo=UTC),
                ),
                optimized_prompt_plan=plan,
            ),
            service.compare_reports(
                model="llama3:latest",
                subset="validation",
                baseline_report=report,
                optimized_report=self._report(
                    average_score=0.5,
                    exact_match_rate=0.25,
                    generated_at=datetime(2026, 6, 7, 11, 0, tzinfo=UTC),
                ),
                optimized_prompt_plan=plan,
            ),
        )

        leaderboard = service.build_optimizer_leaderboard(
            comparisons=comparisons,
            subset="validation",
            model="llama3:latest",
        )

        self.assertEqual(leaderboard.total_runs, 2)
        self.assertEqual(len(leaderboard.entries), 1)
        entry = leaderboard.entries[0]
        self.assertEqual(entry.model, "llama3:latest")
        self.assertEqual(entry.latest_score_delta, 0.2)
        self.assertEqual(entry.average_score_delta, 0.15)

    def test_run_optimizer_sweep_sorts_models_by_score_delta(self) -> None:
        _client, service = self._build_service(
            responses=[
                "# Note\nBad baseline a\n",
                "# Note\nBetter optimized a\n",
                "# Note\nBad baseline b\n",
                "# Note\nBest optimized b\n",
            ]
        )
        examples = (
            self._example(
                example_id="curated::sweep",
                source_note_path="Projects/Note.md",
                title="Note",
                input_markdown="# Note\nBad.\n",
                target_markdown="# Note\n\n## Core\n[[Git]]\n",
            ),
        )
        history_reports = (
            self._report(
                model="model-a",
                average_score=0.2,
                prompt_patch_suggestions=(
                    self._suggestion(
                        error_tag="missing_headings",
                        instruction="Preserve heading hierarchy.",
                        rationale="Keep expected sections.",
                    ),
                ),
            ),
            self._report(
                model="model-b",
                average_score=0.2,
                prompt_patch_suggestions=(
                    self._suggestion(
                        error_tag="missing_links",
                        instruction="Keep grounded links.",
                        rationale="Preserve graph edges.",
                    ),
                ),
            ),
        )

        sweep = service.run_optimizer_sweep(
            models=("model-a", "model-b"),
            examples=examples,
            subset="validation",
            history_reports=history_reports,
            patch_limit=5,
        )

        self.assertEqual(sweep.subset, "validation")
        self.assertEqual(len(sweep.comparisons), 2)
        self.assertGreaterEqual(
            sweep.comparisons[0].score_delta,
            sweep.comparisons[1].score_delta,
        )

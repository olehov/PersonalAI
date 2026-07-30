from __future__ import annotations

from tests.training_eval_test_support import (
    FakeLocalRunnerFactory,
    TrainingEvalServiceTestSupport,
)


class TrainingEvalCoreTests(TrainingEvalServiceTestSupport):
    def test_evaluate_returns_aggregate_metrics_and_per_example_results(self) -> None:
        examples = (
            self._example(
                example_id="curated::exact",
                source_note_path="Projects/Technology Stack.md",
                title="Technology Stack",
                input_markdown="# Technology Stack\nBad.\n",
                target_markdown="# Technology Stack\n\n[[Git]]\n",
            ),
            self._example(
                example_id="synthetic::partial",
                source="synthetic",
                quality_tier="silver",
                task="expand_outline_to_note",
                instruction="Expand the outline.",
                source_note_path="Linux/Processes and Signals.md",
                title="Processes and Signals",
                input_markdown="# Processes and Signals\n- signals\n",
                target_markdown="# Processes and Signals\n\n## Signals\n[[Job Control]]\n",
                tags=("synthetic",),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Technology Stack\n\n[[Git]]\n",
                "# Processes and Signals\n\n## Signals\nSignals overview.\n",
            ]
        )

        report = service.evaluate(
            model="llama3:latest",
            examples=examples,
            subset="validation",
        )

        self.assertEqual(report.model, "llama3:latest")
        self.assertEqual(report.subset, "validation")
        self.assertEqual(len(report.results), 2)
        self.assertEqual(report.results[0].example_id, "curated::exact")
        self.assertTrue(report.results[0].exact_match)
        self.assertEqual(report.results[0].target_link_count, 1)
        self.assertEqual(report.results[0].output_link_count, 1)
        self.assertEqual(report.results[1].example_id, "synthetic::partial")
        self.assertFalse(report.results[1].exact_match)
        self.assertEqual(report.results[1].target_heading_count, 2)
        self.assertEqual(report.results[1].output_heading_count, 2)
        self.assertEqual(len(report.failure_snapshots), 2)
        self.assertEqual(report.failure_snapshots[0].example_id, "synthetic::partial")
        self.assertEqual(report.failure_snapshots[0].error_tags, ("missing_links",))
        self.assertEqual(report.prompt_patch_suggestions[0].error_tag, "missing_links")
        self.assertGreater(report.average_score, 0.5)
        self.assertLess(report.average_score, 1.0)
        self.assertEqual(report.exact_match_rate, 0.5)

    def test_evaluate_classifies_meta_and_heading_failures(self) -> None:
        examples = (
            self._example(
                example_id="curated::taxonomy",
                source_note_path="Bugs/Retries and Timeouts.md",
                title="Retries and Timeouts",
                input_markdown="# Retries and Timeouts\nBad.\n",
                target_markdown="# Retries and Timeouts\n\n## Risks\n[[HTTP]]\n[[Observability]]\n",
            ),
        )
        _client, service = self._build_service(
            responses=[
                "Here is the rewritten note in the Vault House style:\n\n**Retries and Timeouts**\n\n[[HTTP]]\n",
            ]
        )

        report = service.evaluate(
            model="llama3:latest",
            examples=examples,
            subset="validation",
        )

        self.assertEqual(len(report.failure_snapshots), 1)
        self.assertEqual(
            report.failure_snapshots[0].error_tags,
            ("meta_preface", "missing_headings", "missing_links", "style_drift"),
        )
        suggestion_tags = {
            suggestion.error_tag for suggestion in report.prompt_patch_suggestions
        }
        self.assertEqual(
            suggestion_tags,
            {"meta_preface", "missing_headings", "missing_links", "style_drift"},
        )

    def test_evaluate_handles_empty_example_subset(self) -> None:
        _client, service = self._build_service(responses=[])

        report = service.evaluate(
            model="llama3:latest",
            examples=(),
            subset="validation",
        )

        self.assertEqual(report.average_score, 0.0)
        self.assertEqual(report.exact_match_rate, 0.0)
        self.assertEqual(report.results, ())
        self.assertEqual(report.failure_snapshots, ())
        self.assertEqual(report.prompt_patch_suggestions, ())

    def test_evaluate_can_apply_extra_prompt_instructions(self) -> None:
        client, service = self._build_service(responses=["# Note\n"])
        examples = (
            self._example(
                example_id="curated::extra",
                source_note_path="Projects/Note.md",
                title="Note",
                input_markdown="# Note\nBad.\n",
                target_markdown="# Note\n",
            ),
        )

        service.evaluate(
            model="llama3:latest",
            examples=examples,
            subset="validation",
            extra_instructions=("Do not add intro text.",),
        )

        system_prompt = client.calls[0]["messages"][0].content
        self.assertIn("Additional Focus Instructions:", system_prompt)
        self.assertIn("Do not add intro text.", system_prompt)

    def test_evaluate_local_model_uses_local_runner_factory(self) -> None:
        runner_factory = FakeLocalRunnerFactory(
            responses=[
                "# Dijkstra\n\n## Related Notes\n- [Graph Traversal](/Graph Traversal.md)\n",
            ]
        )
        _client, service = self._build_service(
            responses=[],
            local_model_runner_factory=runner_factory,
        )
        examples = (
            self._example(
                example_id="curated::local-model",
                source_note_path="Algorithms/Dijkstra.md",
                title="Dijkstra",
                input_markdown="# Dijkstra\nBad.\n",
                target_markdown="# Dijkstra\n\n## Related Notes\n- [[Graph Traversal]]\n",
            ),
        )

        report = service.evaluate_local_model(
            model_path_or_name="training_examples/fine_tune/mistral_curated/outputs-full-curated",
            model_label="mistral-ft-local",
            examples=examples,
            subset="validation",
            extra_instructions=("Keep links in Obsidian format.",),
        )

        self.assertEqual(
            runner_factory.model_names,
            ["training_examples/fine_tune/mistral_curated/outputs-full-curated"],
        )
        self.assertEqual(report.model, "mistral-ft-local")
        self.assertTrue(report.results[0].exact_match)
        self.assertIn(
            "Additional Focus Instructions:",
            runner_factory.calls[0]["system_prompt"],
        )
        self.assertIn(
            "Keep links in Obsidian format.",
            runner_factory.calls[0]["system_prompt"],
        )

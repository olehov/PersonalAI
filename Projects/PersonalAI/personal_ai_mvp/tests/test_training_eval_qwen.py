from __future__ import annotations

from tests.training_eval_test_support import TrainingEvalServiceTestSupport


class TrainingEvalQwenTests(TrainingEvalServiceTestSupport):
    def test_evaluate_sanitizes_qwen_markdown_links_into_obsidian_links(self) -> None:
        examples = (
            self._example(
                example_id="curated::qwen-links",
                source_note_path="Bugs/Retries and Timeouts.md",
                title="Retries and Timeouts",
                input_markdown="# Retries and Timeouts\nBad.\n",
                target_markdown=(
                    "# Retries and Timeouts\n\n"
                    "## Related Notes\n"
                    "[[Queues and Backpressure]]\n"
                    "[[HTTP]]\n"
                    "[[Observability]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Retries and Timeouts\n\n"
                "## Related Notes\n"
                "[Queues and Backpressure](/Queues%20and%20Backpressure.md)\n"
                "[HTTP](/HTTP.md)\n"
                "[Observability](/Observability.md)\n",
            ]
        )

        report = service.evaluate(
            model="qwen2.5:7b",
            examples=examples,
            subset="validation",
        )

        self.assertEqual(report.results[0].output_markdown, examples[0].target_markdown)
        self.assertTrue(report.results[0].exact_match)
        self.assertEqual(report.results[0].output_link_count, 3)

    def test_evaluate_sanitizes_qwen_plain_related_note_lines(self) -> None:
        examples = (
            self._example(
                example_id="curated::qwen-related-lines",
                source_note_path="Bugs/Retries and Timeouts.md",
                title="Retries and Timeouts",
                input_markdown="# Retries and Timeouts\nBad.\n",
                target_markdown=(
                    "# Retries and Timeouts\n\n"
                    "## Related Notes\n"
                    "[[Queues and Backpressure]]\n"
                    "[[HTTP]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Retries and Timeouts\n\n"
                "## Related Notes\n"
                "- Queues and Backpressure\n"
                "* HTTP\n",
            ]
        )

        report = service.evaluate(
            model="qwen2.5:7b",
            examples=examples,
            subset="validation",
        )

        self.assertEqual(report.results[0].output_markdown, examples[0].target_markdown)
        self.assertTrue(report.results[0].exact_match)

    def test_evaluate_prunes_unsupported_qwen_obsidian_links(self) -> None:
        examples = (
            self._example(
                example_id="curated::qwen-link-prune",
                source_note_path="Bugs/Retries and Timeouts.md",
                title="Retries and Timeouts",
                input_markdown="# Retries and Timeouts\nBad.\n",
                target_markdown=(
                    "# Retries and Timeouts\n\n"
                    "## Core Risks\n"
                    "- Retry storms during outages\n"
                    "\n"
                    "## Related Notes\n"
                    "[[HTTP]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Retries and Timeouts\n\n"
                "## Core Risks\n"
                "- [[Retry Storms During Outages]]\n"
                "\n"
                "## Related Notes\n"
                "[[HTTP]]\n",
            ]
        )

        report = service.evaluate(
            model="qwen2.5:7b",
            examples=examples,
            subset="validation",
        )

        self.assertNotIn(
            "[[Retry Storms During Outages]]",
            report.results[0].output_markdown,
        )
        self.assertIn(
            "- Retry Storms During Outages",
            report.results[0].output_markdown,
        )
        self.assertEqual(report.results[0].output_link_count, 1)

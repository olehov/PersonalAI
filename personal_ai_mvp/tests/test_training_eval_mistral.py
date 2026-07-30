from __future__ import annotations

from tests.training_eval_test_support import TrainingEvalServiceTestSupport


class TrainingEvalMistralTests(TrainingEvalServiceTestSupport):
    def test_evaluate_sanitizes_mistral_wrappers_and_markdown_links(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-wrap",
                source_note_path="Bugs/Retries and Timeouts.md",
                title="Retries and Timeouts",
                input_markdown="# Retries and Timeouts\nBad.\n",
                target_markdown=(
                    "# Retries and Timeouts\n\n"
                    "## Related Notes\n"
                    "- [[Queues and Backpressure]]\n"
                    "- [[HTTP]]\n"
                    "- [[Observability]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "```markdown\n"
                "Title: Retries and Timeouts - Best Practices and Risks\n\n"
                "## Related Notes\n"
                "- [Queues and Backpressure](/vault/Notes/Queues and Backpressure.md)\n"
                "- [HTTP](/vault/Notes/HTTP.md)\n"
                "- [Observability](/vault/Notes/Observability.md)\n"
                "```\n",
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        self.assertTrue(
            report.results[0].output_markdown.startswith("# Retries and Timeouts\n")
        )
        self.assertNotIn("```", report.results[0].output_markdown)
        self.assertNotIn("Title:", report.results[0].output_markdown)
        self.assertIn("[[Queues and Backpressure]]", report.results[0].output_markdown)
        self.assertIn("[[HTTP]]", report.results[0].output_markdown)
        self.assertIn("[[Observability]]", report.results[0].output_markdown)

    def test_evaluate_sanitizes_mistral_path_links_in_body(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-path-links",
                source_note_path="Design Patterns/Queues and Backpressure.md",
                title="Queues and Backpressure",
                input_markdown="# Queues and Backpressure\nBad.\n",
                target_markdown=(
                    "# Queues and Backpressure\n\n"
                    "## Systems Connection\n"
                    "- network-facing services may need backpressure in front of [[HTTP]] handlers\n"
                    "- slow upstream or downstream connections are influenced by [[TCP and UDP]] behavior\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Queues and Backpressure\n\n"
                "## Systems Connection\n"
                "- network-facing services may need backpressure in front of [HTTP](/Note/HTTP) handlers\n"
                "- slow upstream or downstream connections are influenced by [TCP and UDP](/Note/TCP and UDP) behavior\n",
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        self.assertIn("[[HTTP]]", report.results[0].output_markdown)
        self.assertIn("[[TCP and UDP]]", report.results[0].output_markdown)

    def test_evaluate_canonicalizes_mistral_heading_names_by_target_order(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-headings",
                source_note_path="Design Patterns/Queues and Backpressure.md",
                title="Queues and Backpressure",
                input_markdown="# Queues and Backpressure\nBad.\n",
                target_markdown=(
                    "# Queues and Backpressure\n\n"
                    "## Basics\nA.\n\n"
                    "## Why They Matter\nB.\n\n"
                    "## Common Patterns\nC.\n\n"
                    "## Algorithmic Connection\nD.\n\n"
                    "## Systems Connection\nE.\n\n"
                    "## Related Notes\n- [[HTTP]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Queues and Backpressure\n\n"
                "## Key Points\nA.\n\n"
                "## Benefits\nB.\n\n"
                "## Common Implementations\nC.\n\n"
                "## Algorithmic Connections\nD.\n\n"
                "## Systems Connections\nE.\n\n"
                "## Further Reading\n- [[HTTP]]\n",
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        output = report.results[0].output_markdown
        self.assertIn("## Basics", output)
        self.assertIn("## Why They Matter", output)
        self.assertIn("## Common Patterns", output)
        self.assertIn("## Algorithmic Connection", output)
        self.assertIn("## Systems Connection", output)
        self.assertIn("## Related Notes", output)
        self.assertNotIn("## Key Points", output)
        self.assertNotIn("## Benefits", output)

    def test_evaluate_prunes_unsupported_mistral_obsidian_links(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-link-prune",
                source_note_path="Design Patterns/Queues and Backpressure.md",
                title="Queues and Backpressure",
                input_markdown="# Queues and Backpressure\nBad.\n",
                target_markdown=(
                    "# Queues and Backpressure\n\n"
                    "## Basics\n"
                    "- queues decouple producers from consumers\n"
                    "- backpressure limits incoming work when downstream capacity is constrained\n"
                    "\n"
                    "## Related Notes\n"
                    "- [[HTTP]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Queues and Backpressure\n\n"
                "## Basics\n"
                "- [[Queues]] decouple producers from consumers\n"
                "- [[Backpressure]] limits incoming work when downstream capacity is constrained\n"
                "\n"
                "## Related Notes\n"
                "- [[HTTP]]\n",
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        output = report.results[0].output_markdown
        self.assertNotIn("[[Queues]]", output)
        self.assertNotIn("[[Backpressure]]", output)
        self.assertIn("- Queues decouple producers from consumers", output)
        self.assertIn(
            "- Backpressure limits incoming work when downstream capacity is constrained",
            output,
        )
        self.assertEqual(report.results[0].output_link_count, 1)

    def test_evaluate_restores_collapsed_structured_command_sections_for_mistral(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-structured-commands",
                source_note_path="Linux/Job Control.md",
                title="Job Control",
                input_markdown="# Job Control\nBad.\n",
                target_markdown=(
                    "# Job Control\n\n"
                    "## Common Commands\n\n"
                    "### `jobs`\n"
                    "List current shell-managed jobs.\n\n"
                    "### `bg`\n"
                    "Resume a stopped job in the background.\n\n"
                    "### `fg`\n"
                    "Bring a background or stopped job into the foreground.\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Job Control\n\n"
                "## Common Commands\n"
                "- `jobs`: List current shell-managed jobs.\n"
                "- `bg`: Resume a stopped job in the background.\n"
                "- `fg`: Bring a background or stopped job into the foreground.\n",
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        output = report.results[0].output_markdown
        self.assertIn("### `jobs`", output)
        self.assertIn("### `bg`", output)
        self.assertIn("### `fg`", output)
        self.assertNotIn("- `jobs`:", output)

    def test_evaluate_restores_structured_section_schema_for_mistral(self) -> None:
        examples = (
            self._example(
                example_id="curated::mistral-section-schema",
                source_note_path="Linux/Job Control.md",
                title="Job Control",
                input_markdown="# Job Control\nBad.\n",
                target_markdown=(
                    "# Job Control\n\n"
                    "## Basics\n"
                    "Intro.\n\n"
                    "## Core Concepts\n"
                    "- a foreground job receives terminal input directly\n\n"
                    "## Common Commands\n\n"
                    "### `jobs`\n"
                    "List current shell-managed jobs.\n\n"
                    "### `bg`\n"
                    "Resume a stopped job in the background.\n\n"
                    "## Why It Matters\n"
                    "Useful context.\n\n"
                    "## Related Notes\n"
                    "- [[Processes and Signals]]\n"
                ),
            ),
        )
        _client, service = self._build_service(
            responses=[
                "# Job Control\n\n"
                "## Overview\n"
                "Intro.\n\n"
                "## Key Concepts\n"
                "- a foreground job receives terminal input directly\n\n"
                "## Core Commands\n\n"
                "### Listing Jobs\n"
                "`jobs`: List current shell-managed jobs.\n\n"
                "### Resuming a Job\n"
                "`bg`: Resume a stopped job in the background.\n\n"
                "## Importance\n"
                "Useful context.\n\n"
                "## Connected Notes\n"
                "- [[Processes and Signals]]\n"
            ]
        )

        report = service.evaluate(
            model="mistral:7b",
            examples=examples,
            subset="validation",
        )

        output = report.results[0].output_markdown
        self.assertIn("## Basics", output)
        self.assertIn("## Core Concepts", output)
        self.assertIn("## Common Commands", output)
        self.assertIn("## Why It Matters", output)
        self.assertIn("## Related Notes", output)
        self.assertIn("### `jobs`", output)
        self.assertIn("### `bg`", output)
        self.assertNotIn("## Overview", output)
        self.assertNotIn("## Core Commands", output)

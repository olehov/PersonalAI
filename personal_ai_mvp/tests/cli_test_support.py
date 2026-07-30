from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

from cli_app.entry import main
from domain.models import (
    PromptPatchPlan,
    PromptPatchSuggestion,
    TrainingEvaluationExampleResult,
    TrainingEvaluationFailureSnapshot,
    TrainingEvaluationReport,
)


class CliTestSupport(unittest.TestCase):
    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(argv)
        return exit_code, output.getvalue()

    def _run_cli_json(self, argv: list[str]) -> tuple[int, dict[str, object] | list[object]]:
        exit_code, stdout = self._run_cli(argv)
        return exit_code, json.loads(stdout)

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _write_benchmark_pack(
        self,
        root: Path,
        *,
        tasks: list[dict[str, object]],
        pack_id: str = "repo-aware-v1",
        title: str = "Repo Benchmarks",
        description: str = "Repo-aware tasks.",
    ) -> Path:
        pack_path = root / "repo_pack.json"
        pack_path.write_text(
            json.dumps(
                {
                    "pack_id": pack_id,
                    "title": title,
                    "description": description,
                    "tasks": tasks,
                }
            ),
            encoding="utf-8",
        )
        return pack_path

    def _training_result(
        self,
        *,
        example_id: str = "curated::example",
        model: str = "llama3:latest",
        score: float = 0.875,
        exact_match: bool = False,
        output_markdown: str = "# Example\n\nClean.\n",
    ) -> TrainingEvaluationExampleResult:
        return TrainingEvaluationExampleResult(
            example_id=example_id,
            source_note_path=Path("Projects/Example.md"),
            source="curated",
            quality_tier="gold",
            task="rewrite_note_to_house_style",
            model=model,
            score=score,
            exact_match=exact_match,
            target_link_count=1,
            output_link_count=1,
            target_heading_count=2,
            output_heading_count=2,
            output_markdown=output_markdown,
        )

    def _training_failure_snapshot(
        self,
        *,
        example_id: str = "curated::example",
        score: float = 0.875,
        exact_match: bool = False,
        preview: str = "# Example Clean.",
        error_tags: tuple[str, ...] = ("style_drift",),
    ) -> TrainingEvaluationFailureSnapshot:
        return TrainingEvaluationFailureSnapshot(
            example_id=example_id,
            source_note_path=Path("Projects/Example.md"),
            task="rewrite_note_to_house_style",
            score=score,
            exact_match=exact_match,
            output_markdown_preview=preview,
            error_tags=error_tags,
        )

    def _prompt_patch_suggestion(
        self,
        *,
        error_tag: str,
        instruction: str,
        rationale: str,
        occurrences: int = 1,
    ) -> PromptPatchSuggestion:
        return PromptPatchSuggestion(
            error_tag=error_tag,
            occurrences=occurrences,
            instruction=instruction,
            rationale=rationale,
        )

    def _prompt_patch_plan(
        self,
        *,
        base_system_prompt: str = "base",
        optimized_system_prompt: str = "base",
        suggestions: tuple[PromptPatchSuggestion, ...] = (),
    ) -> PromptPatchPlan:
        return PromptPatchPlan(
            base_system_prompt=base_system_prompt,
            optimized_system_prompt=optimized_system_prompt,
            suggestions=suggestions,
        )

    def _training_report(
        self,
        *,
        model: str = "llama3:latest",
        subset: str = "validation",
        average_score: float = 0.0,
        exact_match_rate: float = 0.0,
        results: tuple[TrainingEvaluationExampleResult, ...] = (),
        failure_snapshots: tuple[TrainingEvaluationFailureSnapshot, ...] = (),
        prompt_patch_suggestions: tuple[PromptPatchSuggestion, ...] = (),
    ) -> TrainingEvaluationReport:
        return TrainingEvaluationReport(
            model=model,
            subset=subset,
            average_score=average_score,
            exact_match_rate=exact_match_rate,
            results=results,
            failure_snapshots=failure_snapshots,
            prompt_patch_suggestions=prompt_patch_suggestions,
            generated_at=self._now(),
        )

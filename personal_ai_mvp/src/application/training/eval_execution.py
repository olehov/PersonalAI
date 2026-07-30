"""Execution helpers for training evaluation runs."""

from __future__ import annotations

from typing import Callable

from domain.models import (
    TrainingEvaluationComparison,
    TrainingEvaluationExampleResult,
    TrainingEvaluationReport,
    TrainingExample,
    TrainingOptimizerSweepReport,
)
from application.training.eval_sanitization import (
    sanitize_output_for_model as _sanitize_output_for_model,
)
from application.training.eval_scoring import (
    build_failure_snapshots as _build_failure_snapshots,
    build_prompt_patch_suggestions as _build_prompt_patch_suggestions,
    dedupe_preserve_order as _dedupe_preserve_order,
    heading_count as _heading_count,
    link_count as _link_count,
    score_output as _score_output,
)


def evaluate_examples(
    *,
    model_label: str,
    examples: tuple[TrainingExample, ...],
    subset: str,
    runner: Callable[[TrainingExample], str],
    failure_snapshot_limit: int,
) -> TrainingEvaluationReport:
    """Evaluate a set of training examples with a prepared runner."""
    results: list[TrainingEvaluationExampleResult] = []

    for example in examples:
        output_markdown = runner(example).strip() + "\n"
        output_markdown = _sanitize_output_for_model(
            model=model_label,
            output_markdown=output_markdown,
            example=example,
        )
        score = _score_output(output_markdown, example.target_markdown)
        results.append(
            TrainingEvaluationExampleResult(
                example_id=example.example_id,
                source_note_path=example.source_note_path,
                source=example.source,
                quality_tier=example.quality_tier,
                task=example.task,
                model=model_label,
                score=score,
                exact_match=output_markdown == example.target_markdown,
                target_link_count=_link_count(example.target_markdown),
                output_link_count=_link_count(output_markdown),
                target_heading_count=_heading_count(example.target_markdown),
                output_heading_count=_heading_count(output_markdown),
                output_markdown=output_markdown,
            )
        )

    average_score = (
        sum(result.score for result in results) / len(results)
        if results else 0.0
    )
    exact_match_rate = (
        sum(1 for result in results if result.exact_match) / len(results)
        if results else 0.0
    )
    failure_snapshots = _build_failure_snapshots(
        tuple(results),
        limit=failure_snapshot_limit,
    )
    prompt_patch_suggestions = _build_prompt_patch_suggestions(failure_snapshots)
    return TrainingEvaluationReport(
        model=model_label,
        subset=subset,
        average_score=average_score,
        exact_match_rate=exact_match_rate,
        results=tuple(results),
        failure_snapshots=failure_snapshots,
        prompt_patch_suggestions=prompt_patch_suggestions,
    )


def run_optimizer_sweep(
    *,
    models: tuple[str, ...],
    examples: tuple[TrainingExample, ...],
    subset: str,
    patch_limit: int,
    build_prompt_patch_plan: Callable[..., object],
    evaluate: Callable[..., TrainingEvaluationReport],
    compare_reports: Callable[..., TrainingEvaluationComparison],
    history_reports: tuple[TrainingEvaluationReport, ...],
) -> TrainingOptimizerSweepReport:
    """Run baseline vs optimized comparisons for each unique model."""
    comparisons: list[TrainingEvaluationComparison] = []
    for model in _dedupe_preserve_order(models):
        patch_plan = build_prompt_patch_plan(
            reports=history_reports,
            subset=subset,
            model=model,
            limit=patch_limit,
        )
        baseline_report = evaluate(
            model=model,
            examples=examples,
            subset=subset,
        )
        optimized_report = evaluate(
            model=model,
            examples=examples,
            subset=subset,
            extra_instructions=tuple(
                suggestion.instruction for suggestion in patch_plan.suggestions
            ),
        )
        comparisons.append(
            compare_reports(
                model=model,
                subset=subset,
                baseline_report=baseline_report,
                optimized_report=optimized_report,
                optimized_prompt_plan=patch_plan,
            )
        )

    comparisons.sort(key=lambda item: (-item.score_delta, item.model))
    return TrainingOptimizerSweepReport(
        subset=subset,
        comparisons=tuple(comparisons),
    )

"""Reporting-side helpers for TrainingEvalService."""

from __future__ import annotations

from application.training.eval_execution import run_optimizer_sweep as _run_optimizer_sweep
from application.training.eval_prompting import compare_reports as _compare_reports


def compare_reports(
    *,
    model: str,
    subset: str,
    baseline_report,
    optimized_report,
    optimized_prompt_plan,
):
    """Build a side-by-side comparison between baseline and optimized runs."""
    return _compare_reports(
        model=model,
        subset=subset,
        baseline_report=baseline_report,
        optimized_report=optimized_report,
        optimized_prompt_plan=optimized_prompt_plan,
    )


def run_optimizer_sweep(
    *,
    models: tuple[str, ...],
    examples,
    subset: str,
    patch_limit: int,
    build_prompt_patch_plan,
    evaluate,
    compare_reports,
    history_reports,
):
    """Run optimizer compare loops across multiple models."""
    return _run_optimizer_sweep(
        models=models,
        examples=examples,
        subset=subset,
        patch_limit=patch_limit,
        build_prompt_patch_plan=build_prompt_patch_plan,
        evaluate=evaluate,
        compare_reports=compare_reports,
        history_reports=history_reports,
    )

"""Prompt-building helpers for training evaluation workflows."""

from __future__ import annotations

from collections import Counter

from domain.models import (
    PromptPatchPlan,
    PromptPatchSuggestion,
    TrainingEvaluationComparison,
    TrainingEvaluationReport,
    TrainingExample,
)
from application.training.eval_scoring import (
    dedupe_preserve_order,
    model_profile_suggestions,
)


def build_eval_prompt(example: TrainingExample) -> str:
    """Build the user prompt for one training example rewrite."""
    return (
        f"Task: {example.task}\n"
        f"Title: {example.title}\n"
        f"Instruction: {example.instruction}\n\n"
        "Input note:\n```md\n"
        f"{example.input_markdown}```"
    )


def build_system_prompt(
    *,
    base_system_prompt: str,
    extra_instructions: tuple[str, ...] = (),
) -> str:
    """Build the evaluation system prompt with optional patch instructions."""
    instructions = dedupe_preserve_order(extra_instructions)
    if not instructions:
        return base_system_prompt

    lines = [base_system_prompt, "", "Additional Focus Instructions:"]
    for instruction in instructions:
        lines.append(f"- {instruction}")
    return "\n".join(lines)


def build_prompt_patch_plan(
    *,
    base_system_prompt: str,
    reports: tuple[TrainingEvaluationReport, ...],
    subset: str | None = None,
    model: str | None = None,
    limit: int = 5,
) -> PromptPatchPlan:
    """Build an optimized system prompt plan from evaluation history."""
    filtered_reports = tuple(
        report
        for report in reports
        if (subset is None or report.subset == subset)
        and (model is None or report.model == model)
    )
    fallback_reports = tuple(
        report
        for report in reports
        if subset is None or report.subset == subset
    )
    source_reports = filtered_reports if filtered_reports else fallback_reports
    tag_counter: Counter[str] = Counter()
    suggestion_map: dict[str, PromptPatchSuggestion] = {}
    for report in source_reports:
        for suggestion in report.prompt_patch_suggestions:
            tag_counter[suggestion.error_tag] += suggestion.occurrences
            suggestion_map.setdefault(suggestion.error_tag, suggestion)

    suggestions: list[PromptPatchSuggestion] = []
    for error_tag, occurrences in tag_counter.most_common(limit):
        base = suggestion_map[error_tag]
        suggestions.append(
            PromptPatchSuggestion(
                error_tag=error_tag,
                occurrences=occurrences,
                instruction=base.instruction,
                rationale=base.rationale,
            )
        )

    if model is not None:
        existing_tags = {suggestion.error_tag for suggestion in suggestions}
        for suggestion in model_profile_suggestions(model):
            if suggestion.error_tag in existing_tags:
                continue
            suggestions.append(suggestion)

    optimized_system_prompt = build_system_prompt(
        base_system_prompt=base_system_prompt,
        extra_instructions=tuple(
            suggestion.instruction for suggestion in suggestions
        ),
    )
    return PromptPatchPlan(
        base_system_prompt=base_system_prompt,
        optimized_system_prompt=optimized_system_prompt,
        suggestions=tuple(suggestions),
    )


def compare_reports(
    *,
    model: str,
    subset: str,
    baseline_report: TrainingEvaluationReport,
    optimized_report: TrainingEvaluationReport,
    optimized_prompt_plan: PromptPatchPlan,
) -> TrainingEvaluationComparison:
    """Build a side-by-side comparison between baseline and optimized runs."""
    return TrainingEvaluationComparison(
        model=model,
        subset=subset,
        baseline_report=baseline_report,
        optimized_report=optimized_report,
        optimized_prompt_plan=optimized_prompt_plan,
        score_delta=round(
            optimized_report.average_score - baseline_report.average_score,
            4,
        ),
        exact_match_rate_delta=round(
            optimized_report.exact_match_rate - baseline_report.exact_match_rate,
            4,
        ),
    )

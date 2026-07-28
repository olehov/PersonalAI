"""Persistence and aggregation helpers for training evaluation history."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from domain.models import (
    PromptPatchPlan,
    PromptPatchSuggestion,
    TrainingEvaluationComparison,
    TrainingEvaluationExampleResult,
    TrainingEvaluationFailureSnapshot,
    TrainingEvaluationLeaderboard,
    TrainingEvaluationLeaderboardEntry,
    TrainingEvaluationReport,
    TrainingOptimizerLeaderboard,
    TrainingOptimizerLeaderboardEntry,
)


def append_report(
    *,
    report: TrainingEvaluationReport,
    history_path: Path,
) -> None:
    """Append an evaluation report to a JSONL history file."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    record = serialize_report(report)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def append_comparison(
    *,
    comparison: TrainingEvaluationComparison,
    history_path: Path,
) -> None:
    """Append an evaluation comparison to a JSONL history file."""
    history_path.parent.mkdir(parents=True, exist_ok=True)
    record = serialize_comparison(comparison)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def load_history(
    *,
    history_path: Path,
) -> tuple[TrainingEvaluationReport, ...]:
    """Load saved evaluation reports from a JSONL history file."""
    if not history_path.exists():
        return ()

    reports: list[TrainingEvaluationReport] = []
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            reports.append(deserialize_report(json.loads(line)))
    return tuple(reports)


def load_comparison_history(
    *,
    history_path: Path,
) -> tuple[TrainingEvaluationComparison, ...]:
    """Load saved comparison reports from a JSONL history file."""
    if not history_path.exists():
        return ()

    comparisons: list[TrainingEvaluationComparison] = []
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            comparisons.append(deserialize_comparison(json.loads(line)))
    return tuple(comparisons)


def build_leaderboard(
    *,
    reports: tuple[TrainingEvaluationReport, ...],
    subset: str | None = None,
) -> TrainingEvaluationLeaderboard:
    """Aggregate evaluation history into a compact per-model leaderboard."""
    grouped: dict[tuple[str, str], list[TrainingEvaluationReport]] = defaultdict(list)
    filtered_reports = [
        report for report in reports
        if subset is None or report.subset == subset
    ]
    for report in filtered_reports:
        grouped[(report.model, report.subset)].append(report)

    entries: list[TrainingEvaluationLeaderboardEntry] = []
    for (model, report_subset), model_reports in grouped.items():
        sorted_reports = sorted(model_reports, key=lambda item: item.generated_at)
        latest = sorted_reports[-1]
        previous = sorted_reports[-2] if len(sorted_reports) >= 2 else None
        previous_score = previous.average_score if previous is not None else latest.average_score
        previous_exact_match_rate = (
            previous.exact_match_rate
            if previous is not None
            else latest.exact_match_rate
        )
        best_score = max(item.average_score for item in sorted_reports)
        best_exact_match_rate = max(
            item.exact_match_rate for item in sorted_reports
        )
        entries.append(
            TrainingEvaluationLeaderboardEntry(
                model=model,
                subset=report_subset,
                runs=len(sorted_reports),
                average_score=round(
                    sum(item.average_score for item in sorted_reports) / len(sorted_reports),
                    4,
                ),
                best_score=round(best_score, 4),
                latest_score=latest.average_score,
                delta_vs_previous_score=round(
                    latest.average_score - previous_score,
                    4,
                ),
                delta_vs_best_score=round(
                    latest.average_score - best_score,
                    4,
                ),
                average_exact_match_rate=round(
                    sum(item.exact_match_rate for item in sorted_reports) / len(sorted_reports),
                    4,
                ),
                latest_exact_match_rate=latest.exact_match_rate,
                delta_vs_previous_exact_match_rate=round(
                    latest.exact_match_rate - previous_exact_match_rate,
                    4,
                ),
                delta_vs_best_exact_match_rate=round(
                    latest.exact_match_rate - best_exact_match_rate,
                    4,
                ),
                last_evaluated_at=latest.generated_at,
                latest_failure_snapshots=latest.failure_snapshots,
                prompt_patch_suggestions=latest.prompt_patch_suggestions,
            )
        )

    entries.sort(
        key=lambda entry: (
            -entry.latest_score,
            -entry.average_score,
            -entry.average_exact_match_rate,
            entry.model,
            entry.subset,
        )
    )
    return TrainingEvaluationLeaderboard(
        entries=tuple(entries),
        total_runs=len(filtered_reports),
    )


def build_optimizer_leaderboard(
    *,
    comparisons: tuple[TrainingEvaluationComparison, ...],
    subset: str | None = None,
    model: str | None = None,
) -> TrainingOptimizerLeaderboard:
    """Aggregate comparison history into a compact optimizer leaderboard."""
    grouped: dict[tuple[str, str], list[TrainingEvaluationComparison]] = defaultdict(list)
    filtered = [
        comparison for comparison in comparisons
        if (subset is None or comparison.subset == subset)
        and (model is None or comparison.model == model)
    ]
    for comparison in filtered:
        grouped[(comparison.model, comparison.subset)].append(comparison)

    entries: list[TrainingOptimizerLeaderboardEntry] = []
    for (entry_model, entry_subset), item_comparisons in grouped.items():
        sorted_items = sorted(item_comparisons, key=lambda item: item.generated_at)
        latest = sorted_items[-1]
        entries.append(
            TrainingOptimizerLeaderboardEntry(
                model=entry_model,
                subset=entry_subset,
                runs=len(sorted_items),
                average_score_delta=round(
                    sum(item.score_delta for item in sorted_items) / len(sorted_items),
                    4,
                ),
                best_score_delta=round(
                    max(item.score_delta for item in sorted_items),
                    4,
                ),
                latest_score_delta=latest.score_delta,
                average_exact_match_rate_delta=round(
                    sum(item.exact_match_rate_delta for item in sorted_items) / len(sorted_items),
                    4,
                ),
                latest_exact_match_rate_delta=latest.exact_match_rate_delta,
                last_evaluated_at=latest.generated_at,
            )
        )

    entries.sort(
        key=lambda entry: (
            -entry.latest_score_delta,
            -entry.average_score_delta,
            entry.model,
            entry.subset,
        )
    )
    return TrainingOptimizerLeaderboard(
        entries=tuple(entries),
        total_runs=len(filtered),
    )


def serialize_report(report: TrainingEvaluationReport) -> dict[str, object]:
    """Convert one evaluation report into a JSON-friendly payload."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "model": report.model,
        "subset": report.subset,
        "average_score": report.average_score,
        "exact_match_rate": report.exact_match_rate,
        "results": [
            {
                "example_id": result.example_id,
                "source_note_path": result.source_note_path.as_posix(),
                "source": result.source,
                "quality_tier": result.quality_tier,
                "task": result.task,
                "model": result.model,
                "score": result.score,
                "exact_match": result.exact_match,
                "target_link_count": result.target_link_count,
                "output_link_count": result.output_link_count,
                "target_heading_count": result.target_heading_count,
                "output_heading_count": result.output_heading_count,
                "output_markdown": result.output_markdown,
            }
            for result in report.results
        ],
        "failure_snapshots": [
            {
                "example_id": snapshot.example_id,
                "source_note_path": snapshot.source_note_path.as_posix(),
                "task": snapshot.task,
                "score": snapshot.score,
                "exact_match": snapshot.exact_match,
                "output_markdown_preview": snapshot.output_markdown_preview,
                "error_tags": list(snapshot.error_tags),
            }
            for snapshot in report.failure_snapshots
        ],
        "prompt_patch_suggestions": [
            {
                "error_tag": suggestion.error_tag,
                "occurrences": suggestion.occurrences,
                "instruction": suggestion.instruction,
                "rationale": suggestion.rationale,
            }
            for suggestion in report.prompt_patch_suggestions
        ],
    }


def serialize_comparison(
    comparison: TrainingEvaluationComparison,
) -> dict[str, object]:
    """Convert one evaluation comparison into a JSON-friendly payload."""
    return {
        "generated_at": comparison.generated_at.isoformat(),
        "model": comparison.model,
        "subset": comparison.subset,
        "score_delta": comparison.score_delta,
        "exact_match_rate_delta": comparison.exact_match_rate_delta,
        "baseline_report": serialize_report(comparison.baseline_report),
        "optimized_report": serialize_report(comparison.optimized_report),
        "optimized_prompt_plan": {
            "generated_at": comparison.optimized_prompt_plan.generated_at.isoformat(),
            "base_system_prompt": comparison.optimized_prompt_plan.base_system_prompt,
            "optimized_system_prompt": comparison.optimized_prompt_plan.optimized_system_prompt,
            "suggestions": [
                {
                    "error_tag": suggestion.error_tag,
                    "occurrences": suggestion.occurrences,
                    "instruction": suggestion.instruction,
                    "rationale": suggestion.rationale,
                }
                for suggestion in comparison.optimized_prompt_plan.suggestions
            ],
        },
    }


def deserialize_report(payload: dict[str, object]) -> TrainingEvaluationReport:
    """Restore one evaluation report from a JSON-friendly payload."""
    results = tuple(
        TrainingEvaluationExampleResult(
            example_id=result["example_id"],
            source_note_path=Path(result["source_note_path"]),
            source=result["source"],
            quality_tier=result["quality_tier"],
            task=result["task"],
            model=result["model"],
            score=float(result["score"]),
            exact_match=bool(result["exact_match"]),
            target_link_count=int(result["target_link_count"]),
            output_link_count=int(result["output_link_count"]),
            target_heading_count=int(result["target_heading_count"]),
            output_heading_count=int(result["output_heading_count"]),
            output_markdown=result["output_markdown"],
        )
        for result in payload.get("results", [])
    )
    return TrainingEvaluationReport(
        model=str(payload["model"]),
        subset=str(payload["subset"]),
        average_score=float(payload["average_score"]),
        exact_match_rate=float(payload["exact_match_rate"]),
        results=results,
        failure_snapshots=tuple(
            TrainingEvaluationFailureSnapshot(
                example_id=snapshot["example_id"],
                source_note_path=Path(snapshot["source_note_path"]),
                task=snapshot["task"],
                score=float(snapshot["score"]),
                exact_match=bool(snapshot["exact_match"]),
                output_markdown_preview=snapshot["output_markdown_preview"],
                error_tags=tuple(snapshot.get("error_tags", [])),
            )
            for snapshot in payload.get("failure_snapshots", [])
        ),
        prompt_patch_suggestions=tuple(
            PromptPatchSuggestion(
                error_tag=suggestion["error_tag"],
                occurrences=int(suggestion["occurrences"]),
                instruction=suggestion["instruction"],
                rationale=suggestion["rationale"],
            )
            for suggestion in payload.get("prompt_patch_suggestions", [])
        ),
        generated_at=datetime.fromisoformat(str(payload["generated_at"])),
    )


def deserialize_comparison(payload: dict[str, object]) -> TrainingEvaluationComparison:
    """Restore one evaluation comparison from a JSON-friendly payload."""
    prompt_plan_payload = payload["optimized_prompt_plan"]
    prompt_plan = PromptPatchPlan(
        base_system_prompt=prompt_plan_payload["base_system_prompt"],
        optimized_system_prompt=prompt_plan_payload["optimized_system_prompt"],
        suggestions=tuple(
            PromptPatchSuggestion(
                error_tag=suggestion["error_tag"],
                occurrences=int(suggestion["occurrences"]),
                instruction=suggestion["instruction"],
                rationale=suggestion["rationale"],
            )
            for suggestion in prompt_plan_payload.get("suggestions", [])
        ),
        generated_at=datetime.fromisoformat(str(prompt_plan_payload["generated_at"])),
    )
    return TrainingEvaluationComparison(
        model=str(payload["model"]),
        subset=str(payload["subset"]),
        baseline_report=deserialize_report(payload["baseline_report"]),
        optimized_report=deserialize_report(payload["optimized_report"]),
        optimized_prompt_plan=prompt_plan,
        score_delta=float(payload["score_delta"]),
        exact_match_rate_delta=float(payload["exact_match_rate_delta"]),
        generated_at=datetime.fromisoformat(str(payload["generated_at"])),
    )

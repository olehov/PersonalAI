"""Training and prompt-optimization serializers."""

from __future__ import annotations

from domain.models import (
    PromptPatchPlan,
    PromptPatchSuggestion,
    TrainingCorpus,
    TrainingCorpusManifest,
    TrainingCorpusSplit,
    TrainingEvaluationComparison,
    TrainingEvaluationExampleResult,
    TrainingEvaluationFailureSnapshot,
    TrainingEvaluationLeaderboard,
    TrainingEvaluationLeaderboardEntry,
    TrainingEvaluationReport,
    TrainingExample,
    TrainingFineTuneBundle,
    TrainingFineTuneRecipe,
    TrainingOptimizerLeaderboard,
    TrainingOptimizerLeaderboardEntry,
    TrainingOptimizerSweepReport,
    TrainingTrainerArtifact,
)


def serialize_training_example(example: TrainingExample) -> dict[str, object]:
    return {
        "example_id": example.example_id,
        "source": example.source,
        "quality_tier": example.quality_tier,
        "task": example.task,
        "source_note_path": example.source_note_path.as_posix(),
        "title": example.title,
        "instruction": example.instruction,
        "input_markdown": example.input_markdown,
        "target_markdown": example.target_markdown,
        "tags": list(example.tags),
    }


def serialize_training_corpus(corpus: TrainingCorpus) -> dict[str, object]:
    return {
        "generated_at": corpus.generated_at.isoformat(),
        "examples": [serialize_training_example(example) for example in corpus.examples],
    }


def serialize_training_manifest(manifest: TrainingCorpusManifest) -> dict[str, object]:
    return {
        "generated_at": manifest.generated_at.isoformat(),
        "total_examples": manifest.total_examples,
        "by_source": dict(manifest.by_source),
        "by_quality_tier": dict(manifest.by_quality_tier),
        "by_task": dict(manifest.by_task),
    }


def serialize_training_split(split: TrainingCorpusSplit) -> dict[str, object]:
    return {
        "generated_at": split.generated_at.isoformat(),
        "policy": split.policy,
        "train_examples": [serialize_training_example(example) for example in split.train_examples],
        "validation_examples": [
            serialize_training_example(example) for example in split.validation_examples
        ],
    }


def serialize_training_fine_tune_recipe(recipe: TrainingFineTuneRecipe) -> dict[str, object]:
    return {
        "model_family": recipe.model_family,
        "dataset_format": recipe.dataset_format,
        "recommended_framework": recipe.recommended_framework,
        "learning_rate": recipe.learning_rate,
        "num_epochs": recipe.num_epochs,
        "micro_batch_size": recipe.micro_batch_size,
        "gradient_accumulation_steps": recipe.gradient_accumulation_steps,
        "lora_rank": recipe.lora_rank,
        "lora_alpha": recipe.lora_alpha,
        "lora_dropout": recipe.lora_dropout,
        "max_sequence_length": recipe.max_sequence_length,
        "notes": list(recipe.notes),
    }


def serialize_training_trainer_artifact(
    artifact: TrainingTrainerArtifact,
) -> dict[str, object]:
    return {
        "trainer": artifact.trainer,
        "kind": artifact.kind,
        "path": artifact.path.as_posix(),
        "format": artifact.format,
    }


def serialize_training_fine_tune_bundle(
    bundle: TrainingFineTuneBundle,
) -> dict[str, object]:
    return {
        "generated_at": bundle.generated_at.isoformat(),
        "bundle_dir": bundle.bundle_dir.as_posix(),
        "train_path": bundle.train_path.as_posix(),
        "validation_path": bundle.validation_path.as_posix(),
        "manifest_path": bundle.manifest_path.as_posix(),
        "recipe_path": bundle.recipe_path.as_posix(),
        "runbook_path": bundle.runbook_path.as_posix(),
        "trainer_artifacts": [
            serialize_training_trainer_artifact(artifact)
            for artifact in bundle.trainer_artifacts
        ],
        "source": bundle.source,
        "validation_ratio": bundle.validation_ratio,
        "train_examples": bundle.train_examples,
        "validation_examples": bundle.validation_examples,
        "recipe": serialize_training_fine_tune_recipe(bundle.recipe),
    }


def serialize_training_evaluation_example_result(
    result: TrainingEvaluationExampleResult,
) -> dict[str, object]:
    return {
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


def serialize_training_evaluation_failure_snapshot(
    snapshot: TrainingEvaluationFailureSnapshot,
) -> dict[str, object]:
    return {
        "example_id": snapshot.example_id,
        "source_note_path": snapshot.source_note_path.as_posix(),
        "task": snapshot.task,
        "score": snapshot.score,
        "exact_match": snapshot.exact_match,
        "output_markdown_preview": snapshot.output_markdown_preview,
        "error_tags": list(snapshot.error_tags),
    }


def serialize_prompt_patch_suggestion(
    suggestion: PromptPatchSuggestion,
) -> dict[str, object]:
    return {
        "error_tag": suggestion.error_tag,
        "occurrences": suggestion.occurrences,
        "instruction": suggestion.instruction,
        "rationale": suggestion.rationale,
    }


def serialize_prompt_patch_plan(
    plan: PromptPatchPlan,
) -> dict[str, object]:
    return {
        "generated_at": plan.generated_at.isoformat(),
        "base_system_prompt": plan.base_system_prompt,
        "optimized_system_prompt": plan.optimized_system_prompt,
        "suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in plan.suggestions
        ],
    }


def serialize_training_evaluation_comparison(
    comparison: TrainingEvaluationComparison,
) -> dict[str, object]:
    return {
        "generated_at": comparison.generated_at.isoformat(),
        "model": comparison.model,
        "subset": comparison.subset,
        "score_delta": comparison.score_delta,
        "exact_match_rate_delta": comparison.exact_match_rate_delta,
        "baseline_report": serialize_training_evaluation_report(comparison.baseline_report),
        "optimized_report": serialize_training_evaluation_report(comparison.optimized_report),
        "optimized_prompt_plan": serialize_prompt_patch_plan(comparison.optimized_prompt_plan),
    }


def serialize_training_optimizer_leaderboard_entry(
    entry: TrainingOptimizerLeaderboardEntry,
) -> dict[str, object]:
    return {
        "model": entry.model,
        "subset": entry.subset,
        "runs": entry.runs,
        "average_score_delta": entry.average_score_delta,
        "best_score_delta": entry.best_score_delta,
        "latest_score_delta": entry.latest_score_delta,
        "average_exact_match_rate_delta": entry.average_exact_match_rate_delta,
        "latest_exact_match_rate_delta": entry.latest_exact_match_rate_delta,
        "last_evaluated_at": entry.last_evaluated_at.isoformat(),
    }


def serialize_training_optimizer_leaderboard(
    leaderboard: TrainingOptimizerLeaderboard,
) -> dict[str, object]:
    return {
        "generated_at": leaderboard.generated_at.isoformat(),
        "total_runs": leaderboard.total_runs,
        "entries": [
            serialize_training_optimizer_leaderboard_entry(entry)
            for entry in leaderboard.entries
        ],
    }


def serialize_training_optimizer_sweep_report(
    report: TrainingOptimizerSweepReport,
) -> dict[str, object]:
    return {
        "generated_at": report.generated_at.isoformat(),
        "subset": report.subset,
        "comparisons": [
            serialize_training_evaluation_comparison(comparison)
            for comparison in report.comparisons
        ],
    }


def serialize_training_evaluation_report(
    report: TrainingEvaluationReport,
) -> dict[str, object]:
    return {
        "generated_at": report.generated_at.isoformat(),
        "model": report.model,
        "subset": report.subset,
        "average_score": report.average_score,
        "exact_match_rate": report.exact_match_rate,
        "results": [
            serialize_training_evaluation_example_result(result)
            for result in report.results
        ],
        "failure_snapshots": [
            serialize_training_evaluation_failure_snapshot(snapshot)
            for snapshot in report.failure_snapshots
        ],
        "prompt_patch_suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in report.prompt_patch_suggestions
        ],
    }


def serialize_training_evaluation_leaderboard_entry(
    entry: TrainingEvaluationLeaderboardEntry,
) -> dict[str, object]:
    return {
        "model": entry.model,
        "subset": entry.subset,
        "runs": entry.runs,
        "average_score": entry.average_score,
        "best_score": entry.best_score,
        "latest_score": entry.latest_score,
        "delta_vs_previous_score": entry.delta_vs_previous_score,
        "delta_vs_best_score": entry.delta_vs_best_score,
        "average_exact_match_rate": entry.average_exact_match_rate,
        "latest_exact_match_rate": entry.latest_exact_match_rate,
        "delta_vs_previous_exact_match_rate": entry.delta_vs_previous_exact_match_rate,
        "delta_vs_best_exact_match_rate": entry.delta_vs_best_exact_match_rate,
        "last_evaluated_at": entry.last_evaluated_at.isoformat(),
        "latest_failure_snapshots": [
            serialize_training_evaluation_failure_snapshot(snapshot)
            for snapshot in entry.latest_failure_snapshots
        ],
        "prompt_patch_suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in entry.prompt_patch_suggestions
        ],
    }


def serialize_training_evaluation_leaderboard(
    leaderboard: TrainingEvaluationLeaderboard,
) -> dict[str, object]:
    return {
        "generated_at": leaderboard.generated_at.isoformat(),
        "total_runs": leaderboard.total_runs,
        "entries": [
            serialize_training_evaluation_leaderboard_entry(entry)
            for entry in leaderboard.entries
        ],
    }

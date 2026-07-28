"""Text renderers for training CLI workflows."""

from __future__ import annotations


def render_training_corpus_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for a training corpus."""
    examples = payload["examples"]
    if not examples:
        return "No training examples generated."

    lines = [f"generated_at: {payload['generated_at']}", "examples:"]
    for example in examples:
        lines.append(
            f"- {example['example_id']} | {example['task']} | {example['source_note_path']}"
        )
        if example["tags"]:
            lines.append(f"  tags: {', '.join(example['tags'])}")
    return "\n".join(lines)


def render_training_manifest_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for a manifest."""
    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_examples: {payload['total_examples']}",
        "by_source:",
    ]
    for key, value in payload["by_source"].items():
        lines.append(f"- {key}: {value}")
    lines.append("by_quality_tier:")
    for key, value in payload["by_quality_tier"].items():
        lines.append(f"- {key}: {value}")
    lines.append("by_task:")
    for key, value in payload["by_task"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def render_training_split_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for a split."""
    lines = [
        f"generated_at: {payload['generated_at']}",
        f"policy: {payload['policy']}",
        f"train_examples: {len(payload['train_examples'])}",
        f"validation_examples: {len(payload['validation_examples'])}",
    ]
    return "\n".join(lines)


def render_training_fine_tune_bundle_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for a fine-tune bundle."""
    lines = [
        f"generated_at: {payload['generated_at']}",
        f"bundle_dir: {payload['bundle_dir']}",
        f"train_path: {payload['train_path']}",
        f"validation_path: {payload['validation_path']}",
        f"recipe_path: {payload['recipe_path']}",
        f"runbook_path: {payload['runbook_path']}",
        f"train_examples: {payload['train_examples']}",
        f"validation_examples: {payload['validation_examples']}",
        f"model_family: {payload['recipe']['model_family']}",
        f"recommended_framework: {payload['recipe']['recommended_framework']}",
    ]
    if payload["trainer_artifacts"]:
        lines.append("trainer_artifacts:")
        for artifact in payload["trainer_artifacts"]:
            lines.append(f"- {artifact['trainer']}: {artifact['path']}")
    return "\n".join(lines)


def render_training_evaluation_report_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for an evaluation report."""
    lines = [
        f"generated_at: {payload['generated_at']}",
        f"model: {payload['model']}",
        f"subset: {payload['subset']}",
        f"average_score: {payload['average_score']}",
        f"exact_match_rate: {payload['exact_match_rate']}",
        "results:",
    ]
    for result in payload["results"]:
        lines.append(
            f"- {result['example_id']} | score={result['score']} | exact_match={result['exact_match']}"
        )
    if payload["failure_snapshots"]:
        lines.append("failure_snapshots:")
        for snapshot in payload["failure_snapshots"]:
            lines.append(
                f"- {snapshot['example_id']} | score={snapshot['score']} | "
                f"tags={', '.join(snapshot['error_tags']) if snapshot['error_tags'] else 'none'} | "
                f"preview={snapshot['output_markdown_preview']}"
            )
    if payload["prompt_patch_suggestions"]:
        lines.append("prompt_patch_suggestions:")
        for suggestion in payload["prompt_patch_suggestions"]:
            lines.append(
                f"- {suggestion['error_tag']} x{suggestion['occurrences']} | instruction={suggestion['instruction']}"
            )
    return "\n".join(lines)


def render_training_evaluation_leaderboard_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for an evaluation leaderboard."""
    if not payload["entries"]:
        return "No saved evaluation history."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_runs: {payload['total_runs']}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['model']} | {entry['subset']} | runs={entry['runs']} | "
            f"latest_score={entry['latest_score']} | average_score={entry['average_score']} | "
            f"delta_vs_previous={entry['delta_vs_previous_score']} | delta_vs_best={entry['delta_vs_best_score']}"
        )
        for snapshot in entry["latest_failure_snapshots"]:
            lines.append(
                f"  failure: {snapshot['example_id']} | score={snapshot['score']} | "
                f"tags={', '.join(snapshot['error_tags']) if snapshot['error_tags'] else 'none'} | "
                f"preview={snapshot['output_markdown_preview']}"
            )
        for suggestion in entry["prompt_patch_suggestions"]:
            lines.append(
                f"  patch: {suggestion['error_tag']} x{suggestion['occurrences']} | instruction={suggestion['instruction']}"
            )
    return "\n".join(lines)


def render_prompt_patch_plan_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for a prompt patch plan."""
    lines = [f"generated_at: {payload['generated_at']}", "suggestions:"]
    if payload["suggestions"]:
        for suggestion in payload["suggestions"]:
            lines.append(
                f"- {suggestion['error_tag']} x{suggestion['occurrences']} | {suggestion['instruction']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "optimized_system_prompt:", payload["optimized_system_prompt"]])
    return "\n".join(lines)


def render_training_evaluation_comparison_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for an evaluation comparison."""
    lines = [
        f"generated_at: {payload['generated_at']}",
        f"model: {payload['model']}",
        f"subset: {payload['subset']}",
        f"score_delta: {payload['score_delta']}",
        f"exact_match_rate_delta: {payload['exact_match_rate_delta']}",
        f"baseline_average_score: {payload['baseline_report']['average_score']}",
        f"optimized_average_score: {payload['optimized_report']['average_score']}",
    ]
    return "\n".join(lines)


def render_training_optimizer_leaderboard_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for an optimizer leaderboard."""
    if not payload["entries"]:
        return "No saved optimizer history."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_runs: {payload['total_runs']}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['model']} | {entry['subset']} | runs={entry['runs']} | "
            f"latest_score_delta={entry['latest_score_delta']} | average_score_delta={entry['average_score_delta']}"
        )
    return "\n".join(lines)


def render_training_optimizer_sweep_report_text(payload: dict[str, object]) -> str:
    """Render a compact text summary for an optimizer sweep report."""
    if not payload["comparisons"]:
        return "No optimizer sweep comparisons."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"subset: {payload['subset']}",
        "comparisons:",
    ]
    for comparison in payload["comparisons"]:
        lines.append(
            f"- {comparison['model']} | score_delta={comparison['score_delta']} | "
            f"baseline={comparison['baseline_report']['average_score']} | "
            f"optimized={comparison['optimized_report']['average_score']}"
        )
    return "\n".join(lines)

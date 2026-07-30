"""Support helpers for training-related CLI rendering."""

from cli_app.rendering.training_support.jsonl import (
    render_training_corpus_jsonl,
    select_split_examples,
)
from cli_app.rendering.training_support.text import (
    render_prompt_patch_plan_text,
    render_training_corpus_text,
    render_training_evaluation_comparison_text,
    render_training_evaluation_leaderboard_text,
    render_training_evaluation_report_text,
    render_training_fine_tune_bundle_text,
    render_training_manifest_text,
    render_training_optimizer_leaderboard_text,
    render_training_optimizer_sweep_report_text,
    render_training_split_text,
)

__all__ = [
    "render_prompt_patch_plan_text",
    "render_training_corpus_jsonl",
    "render_training_corpus_text",
    "render_training_evaluation_comparison_text",
    "render_training_evaluation_leaderboard_text",
    "render_training_evaluation_report_text",
    "render_training_fine_tune_bundle_text",
    "render_training_manifest_text",
    "render_training_optimizer_leaderboard_text",
    "render_training_optimizer_sweep_report_text",
    "render_training_split_text",
    "select_split_examples",
]

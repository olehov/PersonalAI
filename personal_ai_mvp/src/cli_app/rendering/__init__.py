"""Grouped CLI rendering helpers."""

from cli_app.rendering.agent import (
    render_agent_history,
    render_agent_runtime_artifact,
)
from cli_app.rendering.basic import (
    render_answer_bundle,
    render_directory_analysis_report,
    render_generated_answer,
    render_note_detail,
    render_note_list,
    render_query_history,
    render_retrieval_bundle,
    render_scan,
)
from cli_app.rendering.benchmark import (
    render_benchmark_compare_result,
    render_benchmark_history,
    render_benchmark_pack,
    render_benchmark_run_result,
)
from cli_app.rendering.notes import (
    render_applied_note_change,
    render_generated_note_application,
    render_generated_note_draft,
    render_maintenance_draft_plan,
    render_maintenance_plan,
    render_maintenance_report,
    render_note_change_proposal,
)
from cli_app.rendering.training import (
    render_prompt_patch_plan,
    render_training_corpus,
    render_training_evaluation_comparison,
    render_training_evaluation_leaderboard,
    render_training_evaluation_report,
    render_training_fine_tune_bundle,
    render_training_manifest,
    render_training_optimizer_leaderboard,
    render_training_optimizer_sweep_report,
    render_training_split,
)

__all__ = [
    "render_agent_history",
    "render_agent_runtime_artifact",
    "render_answer_bundle",
    "render_applied_note_change",
    "render_benchmark_compare_result",
    "render_benchmark_history",
    "render_benchmark_pack",
    "render_benchmark_run_result",
    "render_directory_analysis_report",
    "render_generated_answer",
    "render_generated_note_application",
    "render_generated_note_draft",
    "render_maintenance_draft_plan",
    "render_maintenance_plan",
    "render_maintenance_report",
    "render_note_change_proposal",
    "render_note_detail",
    "render_note_list",
    "render_prompt_patch_plan",
    "render_query_history",
    "render_retrieval_bundle",
    "render_scan",
    "render_training_corpus",
    "render_training_evaluation_comparison",
    "render_training_evaluation_leaderboard",
    "render_training_evaluation_report",
    "render_training_fine_tune_bundle",
    "render_training_manifest",
    "render_training_optimizer_leaderboard",
    "render_training_optimizer_sweep_report",
    "render_training_split",
]

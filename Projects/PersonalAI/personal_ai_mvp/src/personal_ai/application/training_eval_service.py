"""Evaluation harness for generated training examples."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from personal_ai.domain.models import (
    PromptPatchPlan,
    TrainingEvaluationComparison,
    TrainingEvaluationLeaderboard,
    TrainingOptimizerLeaderboard,
    TrainingEvaluationReport,
    TrainingOptimizerSweepReport,
    TrainingExample,
)
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.application.training_eval_history import (
    append_comparison as _append_comparison,
    append_report as _append_report,
    build_leaderboard as _build_leaderboard,
    build_optimizer_leaderboard as _build_optimizer_leaderboard,
    load_comparison_history as _load_comparison_history,
    load_history as _load_history,
)
from personal_ai.application.training_eval_prompting import (
    build_eval_prompt as _build_eval_prompt,
    build_prompt_patch_plan as _build_prompt_patch_plan,
    build_system_prompt as _build_system_prompt,
    compare_reports as _compare_reports,
)
from personal_ai.application.training_eval_execution import (
    evaluate_examples as _evaluate_examples,
    run_optimizer_sweep as _run_optimizer_sweep,
)
from personal_ai.application.training_eval_runners import (
    build_local_model_runner as _build_local_model_runner,
    build_ollama_runner as _build_ollama_runner,
)


class TrainingEvalService:
    """Runs a simple evaluation loop over train/validation examples."""

    SYSTEM_PROMPT = (
        "You rewrite Obsidian markdown notes into the vault house style. "
        "Preserve grounded facts, keep compact structure, use internal [[Note Title]] links, "
        "and avoid meta commentary."
    )
    FAILURE_SNAPSHOT_LIMIT = 3

    def __init__(
        self,
        ollama_client: OllamaClient,
        *,
        local_model_runner_factory: Callable[[str], Callable[[str, str], str]] | None = None,
    ) -> None:
        self._ollama_client = ollama_client
        self._local_model_runner_factory = local_model_runner_factory

    def evaluate(
        self,
        *,
        model: str,
        examples: tuple[TrainingExample, ...],
        subset: str,
        extra_instructions: tuple[str, ...] = (),
    ) -> TrainingEvaluationReport:
        """Evaluates a model over a selected subset of training examples."""
        runner = self._build_ollama_runner(
            model=model,
            extra_instructions=extra_instructions,
        )
        return self._evaluate_with_runner(
            model_label=model,
            examples=examples,
            subset=subset,
            runner=runner,
        )

    def evaluate_local_model(
        self,
        *,
        model_path_or_name: str,
        examples: tuple[TrainingExample, ...],
        subset: str,
        model_label: str | None = None,
        extra_instructions: tuple[str, ...] = (),
    ) -> TrainingEvaluationReport:
        """Evaluates a local Hugging Face/Unsloth model or adapter path over a selected subset."""
        label = model_label or model_path_or_name
        runner, cleanup = self._build_local_model_runner(
            model_path_or_name=model_path_or_name,
            extra_instructions=extra_instructions,
        )
        try:
            return self._evaluate_with_runner(
                model_label=label,
                examples=examples,
                subset=subset,
                runner=runner,
            )
        finally:
            cleanup()

    def _evaluate_with_runner(
        self,
        *,
        model_label: str,
        examples: tuple[TrainingExample, ...],
        subset: str,
        runner: Callable[[TrainingExample], str],
    ) -> TrainingEvaluationReport:
        return _evaluate_examples(
            model_label=model_label,
            examples=examples,
            subset=subset,
            runner=runner,
            failure_snapshot_limit=self.FAILURE_SNAPSHOT_LIMIT,
        )

    def _build_ollama_runner(
        self,
        *,
        model: str,
        extra_instructions: tuple[str, ...],
    ) -> Callable[[TrainingExample], str]:
        return _build_ollama_runner(
            ollama_client=self._ollama_client,
            model=model,
            extra_instructions=extra_instructions,
            build_system_prompt=self.build_system_prompt,
            build_eval_prompt=_build_eval_prompt,
        )

    def _build_local_model_runner(
        self,
        *,
        model_path_or_name: str,
        extra_instructions: tuple[str, ...],
    ) -> tuple[Callable[[TrainingExample], str], Callable[[], None]]:
        return _build_local_model_runner(
            model_path_or_name=model_path_or_name,
            extra_instructions=extra_instructions,
            local_model_runner_factory=self._local_model_runner_factory,
            build_system_prompt=self.build_system_prompt,
            build_eval_prompt=_build_eval_prompt,
        )

    def build_prompt_patch_plan(
        self,
        *,
        reports: tuple[TrainingEvaluationReport, ...],
        subset: str | None = None,
        model: str | None = None,
        limit: int = 5,
    ) -> PromptPatchPlan:
        """Builds an optimized system prompt plan from evaluation history."""
        return _build_prompt_patch_plan(
            base_system_prompt=self.SYSTEM_PROMPT,
            reports=reports,
            subset=subset,
            model=model,
            limit=limit,
        )

    def compare_reports(
        self,
        *,
        model: str,
        subset: str,
        baseline_report: TrainingEvaluationReport,
        optimized_report: TrainingEvaluationReport,
        optimized_prompt_plan: PromptPatchPlan,
    ) -> TrainingEvaluationComparison:
        """Builds a side-by-side comparison between baseline and optimized runs."""
        return _compare_reports(
            model=model,
            subset=subset,
            baseline_report=baseline_report,
            optimized_report=optimized_report,
            optimized_prompt_plan=optimized_prompt_plan,
        )

    def build_system_prompt(
        self,
        *,
        extra_instructions: tuple[str, ...] = (),
    ) -> str:
        """Builds the evaluation system prompt with optional patch instructions."""
        return _build_system_prompt(
            base_system_prompt=self.SYSTEM_PROMPT,
            extra_instructions=extra_instructions,
        )

    def append_report(
        self,
        *,
        report: TrainingEvaluationReport,
        history_path: Path,
    ) -> None:
        """Appends an evaluation report to a JSONL history file."""
        _append_report(report=report, history_path=history_path)

    def append_comparison(
        self,
        *,
        comparison: TrainingEvaluationComparison,
        history_path: Path,
    ) -> None:
        """Appends an evaluation comparison to a JSONL history file."""
        _append_comparison(comparison=comparison, history_path=history_path)

    def load_history(
        self,
        *,
        history_path: Path,
    ) -> tuple[TrainingEvaluationReport, ...]:
        """Loads saved evaluation reports from a JSONL history file."""
        return _load_history(history_path=history_path)

    def load_comparison_history(
        self,
        *,
        history_path: Path,
    ) -> tuple[TrainingEvaluationComparison, ...]:
        """Loads saved comparison reports from a JSONL history file."""
        return _load_comparison_history(history_path=history_path)

    def build_leaderboard(
        self,
        *,
        reports: tuple[TrainingEvaluationReport, ...],
        subset: str | None = None,
    ) -> TrainingEvaluationLeaderboard:
        """Aggregates evaluation history into a compact per-model leaderboard."""
        return _build_leaderboard(
            reports=reports,
            subset=subset,
        )

    def build_optimizer_leaderboard(
        self,
        *,
        comparisons: tuple[TrainingEvaluationComparison, ...],
        subset: str | None = None,
        model: str | None = None,
    ) -> TrainingOptimizerLeaderboard:
        """Aggregates comparison history into a compact optimizer leaderboard."""
        return _build_optimizer_leaderboard(
            comparisons=comparisons,
            subset=subset,
            model=model,
        )

    def run_optimizer_sweep(
        self,
        *,
        models: tuple[str, ...],
        examples: tuple[TrainingExample, ...],
        subset: str,
        history_reports: tuple[TrainingEvaluationReport, ...],
        patch_limit: int = 5,
    ) -> TrainingOptimizerSweepReport:
        """Runs side-by-side baseline vs optimized comparisons for multiple models."""
        return _run_optimizer_sweep(
            models=models,
            examples=examples,
            subset=subset,
            patch_limit=patch_limit,
            build_prompt_patch_plan=self.build_prompt_patch_plan,
            evaluate=self.evaluate,
            compare_reports=self.compare_reports,
            history_reports=history_reports,
        )

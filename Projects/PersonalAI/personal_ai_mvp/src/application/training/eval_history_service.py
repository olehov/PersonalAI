"""Facade over persistence and aggregation for training evaluation history."""

from __future__ import annotations

from pathlib import Path

from application.training.eval_history import (
    append_comparison as _append_comparison,
    append_report as _append_report,
    build_leaderboard as _build_leaderboard,
    build_optimizer_leaderboard as _build_optimizer_leaderboard,
    load_comparison_history as _load_comparison_history,
    load_history as _load_history,
)
from domain.models import (
    TrainingEvaluationComparison,
    TrainingEvaluationLeaderboard,
    TrainingEvaluationReport,
    TrainingOptimizerLeaderboard,
)


class TrainingEvalHistoryService:
    """Provide a small object-oriented façade for eval history concerns."""

    def append_report(
        self,
        *,
        report: TrainingEvaluationReport,
        history_path: Path,
    ) -> None:
        """Append an evaluation report to a JSONL history file."""
        _append_report(report=report, history_path=history_path)

    def append_comparison(
        self,
        *,
        comparison: TrainingEvaluationComparison,
        history_path: Path,
    ) -> None:
        """Append an evaluation comparison to a JSONL history file."""
        _append_comparison(comparison=comparison, history_path=history_path)

    def load_history(
        self,
        *,
        history_path: Path,
    ) -> tuple[TrainingEvaluationReport, ...]:
        """Load saved evaluation reports from a JSONL history file."""
        return _load_history(history_path=history_path)

    def load_comparison_history(
        self,
        *,
        history_path: Path,
    ) -> tuple[TrainingEvaluationComparison, ...]:
        """Load saved comparison reports from a JSONL history file."""
        return _load_comparison_history(history_path=history_path)

    def build_leaderboard(
        self,
        *,
        reports: tuple[TrainingEvaluationReport, ...],
        subset: str | None = None,
    ) -> TrainingEvaluationLeaderboard:
        """Aggregate evaluation history into a compact per-model leaderboard."""
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
        """Aggregate comparison history into a compact optimizer leaderboard."""
        return _build_optimizer_leaderboard(
            comparisons=comparisons,
            subset=subset,
            model=model,
        )

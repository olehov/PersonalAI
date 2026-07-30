"""Execution-side helpers for TrainingEvalService."""

from __future__ import annotations

from typing import Callable

from application.training.eval_execution import evaluate_examples as _evaluate_examples
from application.training.eval_prompting import build_eval_prompt as _build_eval_prompt
from application.training.eval_runners import (
    build_local_model_runner as _build_local_model_runner,
    build_ollama_runner as _build_ollama_runner,
)
from domain.models import TrainingEvaluationReport, TrainingExample


def evaluate_with_runner(
    *,
    model_label: str,
    examples: tuple[TrainingExample, ...],
    subset: str,
    runner: Callable[[TrainingExample], str],
    failure_snapshot_limit: int,
) -> TrainingEvaluationReport:
    """Evaluate one model runner over the provided examples."""
    return _evaluate_examples(
        model_label=model_label,
        examples=examples,
        subset=subset,
        runner=runner,
        failure_snapshot_limit=failure_snapshot_limit,
    )


def build_ollama_runner(
    *,
    ollama_client,
    model: str,
    extra_instructions: tuple[str, ...],
    build_system_prompt,
):
    """Build an Ollama-backed training-eval runner."""
    return _build_ollama_runner(
        ollama_client=ollama_client,
        model=model,
        extra_instructions=extra_instructions,
        build_system_prompt=build_system_prompt,
        build_eval_prompt=_build_eval_prompt,
    )


def build_local_model_runner(
    *,
    model_path_or_name: str,
    extra_instructions: tuple[str, ...],
    local_model_runner_factory,
    build_system_prompt,
):
    """Build a local-model training-eval runner and cleanup callback."""
    return _build_local_model_runner(
        model_path_or_name=model_path_or_name,
        extra_instructions=extra_instructions,
        local_model_runner_factory=local_model_runner_factory,
        build_system_prompt=build_system_prompt,
        build_eval_prompt=_build_eval_prompt,
    )

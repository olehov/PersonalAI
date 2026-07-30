"""Prompt policy helpers for training evaluation workflows."""

from __future__ import annotations

from application.training.eval_prompting import (
    build_prompt_patch_plan as _build_prompt_patch_plan,
    build_system_prompt as _build_system_prompt,
)
from domain.models import PromptPatchPlan, TrainingEvaluationReport

DEFAULT_TRAINING_EVAL_SYSTEM_PROMPT = (
    "You rewrite Obsidian markdown notes into the vault house style. "
    "Preserve grounded facts, keep compact structure, use internal [[Note Title]] links, "
    "and avoid meta commentary."
)


class TrainingEvalPromptPolicy:
    """Owns evaluation prompt policy and prompt optimization rules."""

    def __init__(self, *, base_system_prompt: str = DEFAULT_TRAINING_EVAL_SYSTEM_PROMPT) -> None:
        self._base_system_prompt = base_system_prompt

    @property
    def base_system_prompt(self) -> str:
        """Return the baseline system prompt used for evaluation runs."""
        return self._base_system_prompt

    def build_system_prompt(
        self,
        *,
        extra_instructions: tuple[str, ...] = (),
    ) -> str:
        """Build the evaluation system prompt with optional patch instructions."""
        return _build_system_prompt(
            base_system_prompt=self._base_system_prompt,
            extra_instructions=extra_instructions,
        )

    def build_prompt_patch_plan(
        self,
        *,
        reports: tuple[TrainingEvaluationReport, ...],
        subset: str | None = None,
        model: str | None = None,
        limit: int = 5,
    ) -> PromptPatchPlan:
        """Build an optimized system prompt plan from evaluation history."""
        return _build_prompt_patch_plan(
            base_system_prompt=self._base_system_prompt,
            reports=reports,
            subset=subset,
            model=model,
            limit=limit,
        )

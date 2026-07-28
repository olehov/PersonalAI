from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from application.training.eval_service import TrainingEvalService
from domain.models import (
    PromptPatchSuggestion,
    TrainingEvaluationReport,
    TrainingExample,
)


class FakeOllamaClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def chat(self, *, model: str, messages: tuple[object, ...]) -> str:
        self.calls.append({"model": model, "messages": messages})
        return self._responses.pop(0)


class FakeLocalRunnerFactory:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.model_names: list[str] = []
        self.calls: list[dict[str, str]] = []

    def __call__(self, model_name: str):
        self.model_names.append(model_name)

        def _run(system_prompt: str, user_prompt: str) -> str:
            self.calls.append(
                {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                }
            )
            return self._responses.pop(0)

        return _run


class TrainingEvalServiceTestSupport(unittest.TestCase):
    def _build_service(
        self,
        responses: list[str],
        *,
        local_model_runner_factory: FakeLocalRunnerFactory | None = None,
    ) -> tuple[FakeOllamaClient, TrainingEvalService]:
        client = FakeOllamaClient(responses=responses)
        service = TrainingEvalService(
            client,
            local_model_runner_factory=local_model_runner_factory,
        )
        return client, service

    def _example(
        self,
        *,
        example_id: str,
        source_note_path: str,
        title: str,
        input_markdown: str,
        target_markdown: str,
        source: str = "curated",
        quality_tier: str = "gold",
        task: str = "rewrite_note_to_house_style",
        instruction: str = "Rewrite the note.",
        tags: tuple[str, ...] = ("curated",),
    ) -> TrainingExample:
        return TrainingExample(
            example_id=example_id,
            source=source,
            quality_tier=quality_tier,
            task=task,
            source_note_path=Path(source_note_path),
            title=title,
            instruction=instruction,
            input_markdown=input_markdown,
            target_markdown=target_markdown,
            tags=tags,
        )

    def _build_empty_service(self) -> TrainingEvalService:
        _client, service = self._build_service(responses=[])
        return service

    def _suggestion(
        self,
        *,
        error_tag: str,
        instruction: str,
        rationale: str,
        occurrences: int = 1,
    ) -> PromptPatchSuggestion:
        return PromptPatchSuggestion(
            error_tag=error_tag,
            occurrences=occurrences,
            instruction=instruction,
            rationale=rationale,
        )

    def _report(
        self,
        *,
        model: str = "llama3:latest",
        subset: str = "validation",
        average_score: float = 0.0,
        exact_match_rate: float = 0.0,
        results=(),
        prompt_patch_suggestions: tuple[PromptPatchSuggestion, ...] = (),
        generated_at: datetime | None = None,
    ) -> TrainingEvaluationReport:
        return TrainingEvaluationReport(
            model=model,
            subset=subset,
            average_score=average_score,
            exact_match_rate=exact_match_rate,
            results=results,
            prompt_patch_suggestions=prompt_patch_suggestions,
            generated_at=generated_at or datetime.now(UTC),
        )

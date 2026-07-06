"""Run repo-aware benchmark tasks and persist their artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from personal_ai.application.agent_runtime_service import AgentRuntimeService
from personal_ai.application.benchmark_pack_service import RepoBenchmarkTask
from personal_ai.application.chat_service import ChatService
from personal_ai.application.knowledge_service import (
    serialize_agent_runtime_artifact,
    serialize_generated_answer,
)


@dataclass(frozen=True, slots=True)
class BenchmarkRunResult:
    """One executed benchmark task plus its serialized artifact."""

    pack_id: str
    task_id: str
    category: str
    workflow: str
    model: str
    status: str
    scope_dirs: tuple[str, ...]
    prompt_text: str
    latency_ms: int
    result_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class BenchmarkCompareEntry:
    """One model result inside a benchmark comparison run."""

    model: str
    task_id: str
    workflow: str
    status: str
    latency_ms: int
    result_payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class BenchmarkCompareResult:
    """A side-by-side comparison for one or more benchmark tasks."""

    pack_id: str
    task_ids: tuple[str, ...]
    entries: tuple[BenchmarkCompareEntry, ...]


class BenchmarkRunService:
    """Executes benchmark tasks through existing workflows and logs the artifacts."""

    def __init__(
        self,
        chat_service: ChatService,
        agent_runtime_service: AgentRuntimeService,
        history_repository=None,
    ) -> None:
        self._chat_service = chat_service
        self._agent_runtime_service = agent_runtime_service
        self._history_repository = history_repository

    def run_task(
        self,
        *,
        pack_id: str,
        task: RepoBenchmarkTask,
        model: str,
    ) -> BenchmarkRunResult:
        """Run one benchmark task through its declared workflow."""
        started_at = perf_counter()
        status = "completed"
        if task.workflow == "ask":
            generated = self._chat_service.ask(
                task.prompt,
                model=model,
                scope_dirs=task.scope_dirs,
            )
            result_payload = serialize_generated_answer(generated)
        elif task.workflow == "implementation":
            generated = self._chat_service.scope_implementation(
                task.prompt,
                model=model,
                scope_dirs=task.scope_dirs,
            )
            result_payload = serialize_generated_answer(generated)
        elif task.workflow == "agent":
            artifact = self._agent_runtime_service.run(
                task.prompt,
                model=model,
                scope_dirs=task.scope_dirs,
            )
            result_payload = serialize_agent_runtime_artifact(artifact)
            status = artifact.status
        else:
            raise ValueError(f"Unsupported benchmark workflow: {task.workflow}")

        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        result = BenchmarkRunResult(
            pack_id=pack_id,
            task_id=task.task_id,
            category=task.category,
            workflow=task.workflow,
            model=model,
            status=status,
            scope_dirs=task.scope_dirs,
            prompt_text=task.prompt,
            latency_ms=latency_ms,
            result_payload=result_payload,
        )
        if self._history_repository is not None:
            self._history_repository.save_benchmark_run_result(result)
        return result

    def compare_models(
        self,
        *,
        pack_id: str,
        tasks: tuple[RepoBenchmarkTask, ...],
        models: tuple[str, ...],
    ) -> BenchmarkCompareResult:
        """Run the same benchmark tasks across multiple models and collect results."""
        entries: list[BenchmarkCompareEntry] = []
        for task in tasks:
            for model in models:
                result = self.run_task(
                    pack_id=pack_id,
                    task=task,
                    model=model,
                )
                entries.append(
                    BenchmarkCompareEntry(
                        model=model,
                        task_id=task.task_id,
                        workflow=task.workflow,
                        status=result.status,
                        latency_ms=result.latency_ms,
                        result_payload=result.result_payload,
                    )
                )
        return BenchmarkCompareResult(
            pack_id=pack_id,
            task_ids=tuple(task.task_id for task in tasks),
            entries=tuple(entries),
        )

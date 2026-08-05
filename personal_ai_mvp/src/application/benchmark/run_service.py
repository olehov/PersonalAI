"""Run repo-aware benchmark tasks and persist their artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from application.agent_runtime.service import AgentRuntimeService
from application.benchmark.pack_service import RepoBenchmarkTask
from application.chat.service import ChatService
from application.shared.serializers import (
    serialize_agent_runtime_artifact,
    serialize_generated_answer,
)
from application.web_search.service import WebSearchResponse
from domain.models import PromptMessage


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
        web_search_service=None,
        history_repository=None,
    ) -> None:
        self._chat_service = chat_service
        self._agent_runtime_service = agent_runtime_service
        self._web_search_service = web_search_service
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
        prompt_text = task.prompt
        if task.turns:
            status, prompt_text, result_payload = self._run_multi_turn_task(
                task=task,
                model=model,
            )
        else:
            status, result_payload = self._run_single_turn_workflow(
                workflow=task.workflow,
                prompt=task.prompt,
                model=model,
                scope_dirs=task.scope_dirs,
                web_grounding_mode=task.web_grounding_mode,
                web_grounding_query=task.web_grounding_query,
            )

        result_payload = self._attach_benchmark_metadata(
            payload=result_payload,
            task=task,
        )
        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        result = BenchmarkRunResult(
            pack_id=pack_id,
            task_id=task.task_id,
            category=task.category,
            workflow=task.workflow,
            model=model,
            status=status,
            scope_dirs=task.scope_dirs,
            prompt_text=prompt_text,
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

    def _run_single_turn_workflow(
        self,
        *,
        workflow: str,
        prompt: str,
        model: str,
        scope_dirs: tuple[str, ...],
        conversation_history: tuple[PromptMessage, ...] = (),
        web_grounding_mode: str = "disabled",
        web_grounding_query: str = "",
    ) -> tuple[str, dict[str, object]]:
        web_search_response = self._resolve_web_grounding_response(
            workflow=workflow,
            prompt=prompt,
            web_grounding_mode=web_grounding_mode,
            web_grounding_query=web_grounding_query,
        )
        if workflow == "ask":
            generated = self._chat_service.ask(
                prompt,
                model=model,
                scope_dirs=scope_dirs,
                conversation_history=conversation_history,
                web_search_response=web_search_response,
            )
            return "completed", self._attach_web_grounding_details(
                payload=serialize_generated_answer(generated),
                web_grounding_mode=web_grounding_mode,
                web_grounding_query=web_grounding_query,
                web_search_response=web_search_response,
            )
        if workflow == "implementation":
            generated = self._chat_service.scope_implementation(
                prompt,
                model=model,
                scope_dirs=scope_dirs,
                conversation_history=conversation_history,
                web_search_response=web_search_response,
            )
            return "completed", self._attach_web_grounding_details(
                payload=serialize_generated_answer(generated),
                web_grounding_mode=web_grounding_mode,
                web_grounding_query=web_grounding_query,
                web_search_response=web_search_response,
            )
        if workflow == "agent":
            artifact = self._agent_runtime_service.run(
                prompt,
                model=model,
                scope_dirs=scope_dirs,
                conversation_history=conversation_history,
            )
            return artifact.status, self._attach_web_grounding_details(
                payload=serialize_agent_runtime_artifact(artifact),
                web_grounding_mode=web_grounding_mode,
                web_grounding_query=web_grounding_query,
                web_search_response=web_search_response,
            )
        raise ValueError(f"Unsupported benchmark workflow: {workflow}")

    def _run_multi_turn_task(
        self,
        *,
        task: RepoBenchmarkTask,
        model: str,
    ) -> tuple[str, str, dict[str, object]]:
        conversation_history: tuple[PromptMessage, ...] = ()
        turn_results: list[dict[str, object]] = []
        final_status = "completed"

        for index, turn in enumerate(task.turns, start=1):
            turn_status, turn_payload = self._run_single_turn_workflow(
                workflow=task.workflow,
                prompt=turn.prompt,
                model=model,
                scope_dirs=task.scope_dirs,
                conversation_history=conversation_history,
                web_grounding_mode=task.web_grounding_mode,
                web_grounding_query=task.web_grounding_query,
            )
            turn_results.append(
                {
                    "turn_index": index,
                    "prompt": turn.prompt,
                    "expected_signals": list(turn.expected_signals),
                    "anti_signals": list(turn.anti_signals),
                    "notes": list(turn.notes),
                    "status": turn_status,
                    "result_payload": turn_payload,
                }
            )
            conversation_history = (
                *conversation_history,
                PromptMessage(role="user", content=turn.prompt),
                PromptMessage(
                    role="assistant",
                    content=self._extract_assistant_content(turn_payload),
                ),
            )
            final_status = turn_status

        primary_prompt = task.prompt or task.turns[0].prompt
        final_payload = turn_results[-1]["result_payload"] if turn_results else {}
        return (
            final_status,
            primary_prompt,
            {
                "multi_turn": True,
                "turn_count": len(turn_results),
                "final_status": final_status,
                "final_payload": final_payload,
                "turn_results": turn_results,
            },
        )

    def _resolve_web_grounding_response(
        self,
        *,
        workflow: str,
        prompt: str,
        web_grounding_mode: str,
        web_grounding_query: str,
    ) -> WebSearchResponse | None:
        normalized_mode = (web_grounding_mode or "disabled").strip().lower()
        if normalized_mode == "disabled":
            return None
        if workflow not in {"ask", "implementation"}:
            return None
        if self._web_search_service is None:
            return None
        query = (web_grounding_query or prompt).strip()
        if not query:
            return None
        return self._web_search_service.search(query)

    def _attach_benchmark_metadata(
        self,
        *,
        payload: dict[str, object],
        task: RepoBenchmarkTask,
    ) -> dict[str, object]:
        updated = dict(payload)
        metadata = dict(updated.get("benchmark_metadata", {}))
        metadata.setdefault("task_id", task.task_id)
        metadata.setdefault("workflow", task.workflow)
        metadata.setdefault("scope_dirs", list(task.scope_dirs))
        metadata.setdefault("web_grounding_mode", task.web_grounding_mode)
        metadata.setdefault("web_grounding_query", task.web_grounding_query)
        updated["benchmark_metadata"] = metadata
        return updated

    def _attach_web_grounding_details(
        self,
        *,
        payload: dict[str, object],
        web_grounding_mode: str,
        web_grounding_query: str,
        web_search_response: WebSearchResponse | None,
    ) -> dict[str, object]:
        updated = dict(payload)
        metadata = dict(updated.get("benchmark_metadata", {}))
        metadata.update(
            {
                "web_grounding_mode": web_grounding_mode,
                "web_grounding_query": web_grounding_query,
                "web_grounding_used": web_search_response is not None,
            }
        )
        if web_search_response is not None:
            metadata.update(
                {
                    "web_grounding_provider": web_search_response.provider,
                    "web_grounding_enabled": web_search_response.enabled,
                    "web_grounding_degraded": web_search_response.degraded,
                    "web_grounding_error": web_search_response.error,
                    "web_grounding_result_count": len(web_search_response.results),
                    "web_grounding_effective_query": web_search_response.query,
                }
            )
        updated["benchmark_metadata"] = metadata
        return updated

    def _extract_assistant_content(self, payload: dict[str, object]) -> str:
        answer_text = payload.get("answer_text")
        if isinstance(answer_text, str) and answer_text.strip():
            return answer_text

        final_output = payload.get("final_output")
        if isinstance(final_output, str) and final_output.strip():
            return final_output

        status = payload.get("status")
        if isinstance(status, str) and status.strip():
            return f"Status: {status}"
        return "No assistant content returned."


__all__ = [
    "BenchmarkCompareEntry",
    "BenchmarkCompareResult",
    "BenchmarkRunResult",
    "BenchmarkRunService",
]

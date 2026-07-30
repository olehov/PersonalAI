"""Application/controller layer for the PersonalAI web UI."""

from __future__ import annotations

from pathlib import Path

from application.chat.preprocessor import PromptPreprocessResult
from application.shared.serializers import (
    serialize_agent_run_history_entry,
    serialize_agent_runtime_artifact,
    serialize_benchmark_run_history_entry,
    serialize_directory_analysis_report,
    serialize_generated_answer,
    serialize_generated_note_draft,
    serialize_query_history_entry,
)
from domain.models import PromptMessage
from infrastructure.config.settings import get_settings
from web_app.app_support.assets import (
    frontend_index_path as _frontend_index_path,
    has_frontend_assets as _has_frontend_assets,
    resolve_frontend_asset as _resolve_frontend_asset,
)
from web_app.app_support.bootstrap import (
    build_runtime_components,
)
from web_app.app_support.history import (
    health_status as _health_status,
    history_overview as _history_overview,
    list_agent_history as _list_agent_history,
    list_ask_history as _list_ask_history,
    list_benchmark_history as _list_benchmark_history,
)
from web_app.app_support.payloads import (
    serialize_preprocess_result,
)
from web_app.api_helpers import (
    normalize_reasoning_mode,
    parse_scope_dirs,
    serialize_route_decision,
)

DEFAULT_UI_MODEL = get_settings().default_model


class PersonalAIWebApp:
    """Thin controller layer for the local web UI."""

    def __init__(
        self,
        *,
        vault_root: Path,
        ollama_base_url: str | None = None,
        ollama_timeout_seconds: int | None = None,
        frontend_dist_dir: Path | None = None,
    ) -> None:
        settings = get_settings()
        self._settings = settings
        self._frontend_dist_dir = frontend_dist_dir or settings.frontend_dist_dir
        components = build_runtime_components(
            vault_root=vault_root,
            settings=settings,
            ollama_base_url=ollama_base_url,
            ollama_timeout_seconds=ollama_timeout_seconds,
        )
        self._knowledge = components["knowledge"]
        self._directory_analysis = components["directory_analysis"]
        self._router = components["router"]
        self._ollama_client = components["ollama_client"]
        self._prompt_preprocessor = components["prompt_preprocessor"]
        self._history_repository = components["history_repository"]
        self._chat = components["chat"]
        self._agent_runtime = components["agent_runtime"]
        self._drafts = components["drafts"]

    def _resolve_request_model(self, requested_model: str, *, workflow: str) -> str:
        """Resolve the effective model for one workflow when the UI sends no explicit model."""
        normalized = requested_model.strip()
        if normalized:
            return normalized
        if workflow == "agent":
            return self._settings.agent_default_model
        return self._settings.default_model

    def _build_execution_payload(
        self,
        *,
        requested_workflow: str,
        executed_workflow: str,
        requested_model: str,
        resolved_model: str | None,
        reasoning_mode: str | None = None,
        route_workflow: str | None = None,
    ) -> dict[str, object]:
        """Build a compact debug payload describing how the request was executed."""
        return {
            "requested_workflow": requested_workflow,
            "executed_workflow": executed_workflow,
            "route_workflow": route_workflow,
            "requested_model": requested_model.strip() or None,
            "resolved_model": resolved_model.strip() if isinstance(resolved_model, str) and resolved_model.strip() else None,
            "reasoning_mode": reasoning_mode,
        }

    def reload(self) -> None:
        """Reload the vault index."""
        self._knowledge.load()

    def ask(
        self,
        *,
        question: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        prepared: PromptPreprocessResult | None = None,
    ) -> dict[str, object]:
        """Run a grounded answer request."""
        prepared = prepared or self._prompt_preprocessor.preprocess(question, workflow_hint="ask")
        resolved_model = self._resolve_request_model(model, workflow="ask")
        answer = self._chat.ask(
            prepared.processed_text,
            model=resolved_model,
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )
        payload = serialize_generated_answer(answer)
        payload["preprocess"] = serialize_preprocess_result(prepared)
        payload["execution"] = self._build_execution_payload(
            requested_workflow="ask",
            executed_workflow="ask",
            requested_model=model,
            resolved_model=resolved_model,
            reasoning_mode=reasoning_mode,
        )
        return payload

    def scope_implementation(
        self,
        *,
        request_text: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        prepared: PromptPreprocessResult | None = None,
    ) -> dict[str, object]:
        """Generate a scoped implementation breakdown for a project-scale request."""
        prepared = prepared or self._prompt_preprocessor.preprocess(
            request_text,
            workflow_hint="implementation",
        )
        resolved_model = self._resolve_request_model(model, workflow="implementation")
        answer = self._chat.scope_implementation(
            prepared.processed_text,
            model=resolved_model,
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )
        payload = serialize_generated_answer(answer)
        payload["preprocess"] = serialize_preprocess_result(prepared)
        payload["execution"] = self._build_execution_payload(
            requested_workflow="implementation",
            executed_workflow="implementation",
            requested_model=model,
            resolved_model=resolved_model,
            reasoning_mode=reasoning_mode,
        )
        return payload

    def run_agent(
        self,
        *,
        request_text: str,
        model: str,
        scope_text: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
        discussion_preset: str | None = None,
        prepared: PromptPreprocessResult | None = None,
    ) -> dict[str, object]:
        """Run the planning-oriented agent runtime."""
        prepared = prepared or self._prompt_preprocessor.preprocess(
            request_text,
            workflow_hint="agent",
        )
        resolved_model = self._resolve_request_model(model, workflow="agent")
        artifact = self._agent_runtime.run(
            prepared.processed_text,
            model=resolved_model,
            scope_dirs=parse_scope_dirs(scope_text),
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
            discussion_preset=discussion_preset,
        )
        payload = serialize_agent_runtime_artifact(artifact)
        payload["preprocess"] = serialize_preprocess_result(prepared)
        payload["execution"] = self._build_execution_payload(
            requested_workflow="agent",
            executed_workflow="agent",
            requested_model=model,
            resolved_model=resolved_model,
            reasoning_mode=reasoning_mode,
        )
        return payload

    def draft_note(
        self,
        *,
        title: str,
        instruction: str,
        model: str,
        target_dir: str,
        scope_text: str,
        prepared: PromptPreprocessResult | None = None,
    ) -> dict[str, object]:
        """Generate a safe note draft proposal."""
        prepared = prepared or self._prompt_preprocessor.preprocess(
            instruction,
            workflow_hint="draft",
        )
        resolved_model = self._resolve_request_model(model, workflow="draft")
        draft = self._drafts.draft_note(
            title=title.strip(),
            instruction=prepared.processed_text,
            model=resolved_model,
            target_dir=target_dir.strip() or None,
            scope_dirs=parse_scope_dirs(scope_text),
        )
        payload = serialize_generated_note_draft(draft)
        payload["preprocess"] = serialize_preprocess_result(prepared)
        payload["execution"] = self._build_execution_payload(
            requested_workflow="draft",
            executed_workflow="draft",
            requested_model=model,
            resolved_model=resolved_model,
            reasoning_mode=None,
        )
        return payload

    def analyze_directory(self, *, directory: str) -> dict[str, object]:
        """Analyze a whole vault directory and return a JSON-friendly report."""
        report = self._directory_analysis.analyze_directory(directory.strip())
        payload = serialize_directory_analysis_report(report)
        payload["execution"] = self._build_execution_payload(
            requested_workflow="analyze",
            executed_workflow="analyze",
            requested_model="",
            resolved_model=None,
            reasoning_mode=None,
        )
        return payload

    def auto_route(
        self,
        *,
        prompt: str,
        conversation_history: tuple[PromptMessage, ...] = (),
        title: str = "",
        directory: str = "",
        target_dir: str = "",
    ) -> dict[str, object]:
        """Return the backend routing decision for one request."""
        prepared = self._prompt_preprocessor.preprocess(
            prompt,
            workflow_hint="route",
        )
        decision = self._router.route_request(
            prompt=prepared.processed_text,
            conversation_history=conversation_history,
            title=title.strip(),
            directory=directory.strip(),
            target_dir=target_dir.strip(),
        )
        return {
            "decision": serialize_route_decision(decision),
            "preprocess": serialize_preprocess_result(prepared),
        }

    def auto_run(
        self,
        *,
        prompt: str,
        model: str,
        scope_text: str,
        title: str = "",
        directory: str = "",
        target_dir: str = "",
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "auto",
        discussion_preset: str | None = None,
    ) -> dict[str, object]:
        """Route the request automatically and execute the selected workflow."""
        prepared = self._prompt_preprocessor.preprocess(
            prompt,
            workflow_hint="auto",
        )
        decision = self._router.route_request(
            prompt=prepared.processed_text,
            conversation_history=conversation_history,
            title=title.strip(),
            directory=directory.strip(),
            target_dir=target_dir.strip(),
        )
        route_payload = serialize_route_decision(decision)
        effective_reasoning_mode = (
            decision.reasoning_mode if reasoning_mode == "auto" else normalize_reasoning_mode(reasoning_mode)
        )
        if decision.workflow == "agent":
            result = self.run_agent(
                request_text=prepared.processed_text,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
                discussion_preset=discussion_preset,
                prepared=prepared,
            )
        elif decision.workflow == "implementation":
            result = self.scope_implementation(
                request_text=prepared.processed_text,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
                prepared=prepared,
            )
        elif decision.workflow == "draft":
            result = self.draft_note(
                title=decision.derived_title or title or "Draft Note",
                instruction=prepared.processed_text,
                model=model,
                target_dir=target_dir or "Inbox",
                scope_text=scope_text,
                prepared=prepared,
            )
        elif decision.workflow == "analyze":
            resolved_directory = decision.derived_directory or directory
            if not resolved_directory:
                raise ValueError(
                    "Auto-routing selected directory analysis but no directory could be inferred."
                )
            result = self.analyze_directory(directory=resolved_directory)
        else:
            result = self.ask(
                question=prepared.processed_text,
                model=model,
                scope_text=scope_text,
                conversation_history=conversation_history,
                reasoning_mode=effective_reasoning_mode,
                prepared=prepared,
            )
        return {
            "route": route_payload,
            "preprocess": serialize_preprocess_result(prepared),
            "reasoning_mode": effective_reasoning_mode,
            "result": result,
            "execution": self._build_execution_payload(
                requested_workflow="auto",
                executed_workflow=decision.workflow,
                requested_model=model,
                resolved_model=result.get("execution", {}).get("resolved_model") if isinstance(result, dict) else None,
                reasoning_mode=effective_reasoning_mode,
                route_workflow=decision.workflow,
            ),
        }

    def list_ask_history(self, *, limit: int) -> list[dict[str, object]]:
        """Return recent grounded ask/scope history entries."""
        return _list_ask_history(self._history_repository, limit=limit)

    def list_agent_history(self, *, limit: int) -> list[dict[str, object]]:
        """Return recent persisted agent-runtime history entries."""
        return _list_agent_history(self._history_repository, limit=limit)

    def list_benchmark_history(self, *, limit: int) -> list[dict[str, object]]:
        """Return recent persisted benchmark run history entries."""
        return _list_benchmark_history(self._history_repository, limit=limit)

    def history_overview(self) -> dict[str, int]:
        """Return per-stream history counts for the UI."""
        return _history_overview(self._history_repository)

    def health_status(self) -> dict[str, object]:
        """Return a compact health payload for runtime supervision."""
        return _health_status(
            knowledge=self._knowledge,
            has_frontend_assets=self.has_frontend_assets(),
        )

    def list_models(self) -> list[str]:
        """Return locally available Ollama model names."""
        return self._ollama_client.list_models()

    def update_agent_task_plan(
        self,
        *,
        entry_id: int,
        task_plan: dict[str, object],
    ) -> dict[str, object]:
        """Persist one task-plan update for a saved agent runtime entry."""
        updated = self._history_repository.update_agent_runtime_task_plan(
            entry_id=entry_id,
            task_plan_payload=task_plan,
        )
        if updated is None or updated.artifact_payload is None:
            raise ValueError(f"Agent history entry not found: {entry_id}")
        return updated.artifact_payload

    def frontend_dist_dir(self) -> Path:
        """Return the configured frontend distribution directory."""
        return self._frontend_dist_dir

    def frontend_index_path(self) -> Path:
        """Return the expected React entrypoint HTML path."""
        return _frontend_index_path(self._frontend_dist_dir)

    def has_frontend_assets(self) -> bool:
        """Return whether the built JS frontend is available."""
        return _has_frontend_assets(self._frontend_dist_dir)

    def resolve_frontend_asset(self, request_path: str) -> Path:
        """Resolve a frontend asset path inside the built distribution directory."""
        return _resolve_frontend_asset(self._frontend_dist_dir, request_path)

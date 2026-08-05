"""CLI runtime wiring for PersonalAI services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.agent_runtime.service import AgentRuntimeService
from application.benchmark.pack_service import BenchmarkPackService
from application.benchmark.run_service import BenchmarkRunService
from application.chat.service import ChatService
from application.knowledge.answer_service import AnswerService
from application.knowledge.directory_analysis_service import DirectoryAnalysisService
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.notes.draft_service import NoteDraftService
from application.notes.maintenance_service import KnowledgeMaintenanceService
from application.notes.mutation_service import NoteMutationService
from application.notes.policy import NotePolicy
from application.training.corpus_service import TrainingCorpusService
from application.training.eval_service import TrainingEvalService
from application.training.fine_tune_service import TrainingFineTuneService
from infrastructure.llm.ollama_client import OllamaClient
from infrastructure.llm.model_client import ModelClient
from infrastructure.llm.openai_responses_client import OpenAIResponsesClient
from infrastructure.history.repository import SQLiteQueryHistoryRepository
from infrastructure.llm.routing_model_client import RoutingModelClient
from infrastructure.config.settings import get_settings
from infrastructure.web_search.factory import build_web_search_service


@dataclass(frozen=True)
class CliRuntime:
    """Resolved service graph for CLI command execution."""

    knowledge_service: KnowledgeService
    retrieval_service: RetrievalService
    directory_analysis_service: DirectoryAnalysisService
    answer_service: AnswerService
    ollama_client: ModelClient
    history_repository: SQLiteQueryHistoryRepository
    web_search_service: object
    chat_service: ChatService
    agent_runtime_service: AgentRuntimeService
    mutation_service: NoteMutationService
    draft_service: NoteDraftService
    maintenance_service: KnowledgeMaintenanceService
    benchmark_pack_service: BenchmarkPackService
    benchmark_run_service: BenchmarkRunService
    training_corpus_service: TrainingCorpusService
    training_eval_service: TrainingEvalService
    training_fine_tune_service: TrainingFineTuneService


def build_cli_runtime(
    *,
    vault_root: Path,
    history_db_path: Path,
    ollama_base_url: str,
    ollama_timeout_seconds: int | None,
) -> CliRuntime:
    """Build the service graph used by CLI command handlers."""
    knowledge_service = KnowledgeService(vault_root)
    knowledge_service.load()
    retrieval_service = RetrievalService(knowledge_service)
    directory_analysis_service = DirectoryAnalysisService(knowledge_service)
    answer_service = AnswerService(retrieval_service)
    settings = get_settings()
    ollama_client = OllamaClient(
        base_url=ollama_base_url,
        timeout_seconds=ollama_timeout_seconds,
    )
    openai_client = OpenAIResponsesClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout_seconds=settings.openai_timeout_seconds,
        configured_models=settings.openai_models,
    )
    model_client = RoutingModelClient(
        ollama_client=ollama_client,
        openai_client=openai_client,
        serialize_ollama_requests=settings.serialize_ollama_requests,
    )
    history_repository = SQLiteQueryHistoryRepository(history_db_path)
    web_search_service = build_web_search_service(settings)
    chat_service = ChatService(answer_service, model_client, history_repository)
    agent_runtime_service = AgentRuntimeService(
        knowledge_service,
        answer_service,
        model_client,
        history_repository,
    )
    mutation_service = NoteMutationService(knowledge_service, NotePolicy(vault_root))
    draft_service = NoteDraftService(answer_service, mutation_service, model_client)
    maintenance_service = KnowledgeMaintenanceService(knowledge_service, mutation_service)
    benchmark_pack_service = BenchmarkPackService()
    benchmark_run_service = BenchmarkRunService(
        chat_service,
        agent_runtime_service,
        web_search_service,
        history_repository,
    )
    training_corpus_service = TrainingCorpusService(knowledge_service)
    training_eval_service = TrainingEvalService(model_client)
    training_fine_tune_service = TrainingFineTuneService(training_corpus_service)
    return CliRuntime(
        knowledge_service=knowledge_service,
        retrieval_service=retrieval_service,
        directory_analysis_service=directory_analysis_service,
        answer_service=answer_service,
        ollama_client=model_client,
        history_repository=history_repository,
        web_search_service=web_search_service,
        chat_service=chat_service,
        agent_runtime_service=agent_runtime_service,
        mutation_service=mutation_service,
        draft_service=draft_service,
        maintenance_service=maintenance_service,
        benchmark_pack_service=benchmark_pack_service,
        benchmark_run_service=benchmark_run_service,
        training_corpus_service=training_corpus_service,
        training_eval_service=training_eval_service,
        training_fine_tune_service=training_fine_tune_service,
    )


__all__ = [
    "CliRuntime",
    "build_cli_runtime",
]

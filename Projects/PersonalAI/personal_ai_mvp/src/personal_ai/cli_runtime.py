"""CLI runtime wiring for PersonalAI services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from personal_ai.application import (
    AgentRuntimeService,
    AnswerService,
    BenchmarkPackService,
    BenchmarkRunService,
    ChatService,
    DirectoryAnalysisService,
    KnowledgeMaintenanceService,
    KnowledgeService,
    NoteDraftService,
    NoteMutationService,
    NotePolicy,
    RetrievalService,
    TrainingCorpusService,
    TrainingEvalService,
    TrainingFineTuneService,
)
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.query_history_repository import SQLiteQueryHistoryRepository


@dataclass(frozen=True)
class CliRuntime:
    """Resolved service graph for CLI command execution."""

    knowledge_service: KnowledgeService
    retrieval_service: RetrievalService
    directory_analysis_service: DirectoryAnalysisService
    answer_service: AnswerService
    ollama_client: OllamaClient
    history_repository: SQLiteQueryHistoryRepository
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
    ollama_client = OllamaClient(
        base_url=ollama_base_url,
        timeout_seconds=ollama_timeout_seconds,
    )
    history_repository = SQLiteQueryHistoryRepository(history_db_path)
    chat_service = ChatService(answer_service, ollama_client, history_repository)
    agent_runtime_service = AgentRuntimeService(
        knowledge_service,
        answer_service,
        ollama_client,
        history_repository,
    )
    mutation_service = NoteMutationService(knowledge_service, NotePolicy(vault_root))
    draft_service = NoteDraftService(answer_service, mutation_service, ollama_client)
    maintenance_service = KnowledgeMaintenanceService(knowledge_service, mutation_service)
    benchmark_pack_service = BenchmarkPackService()
    benchmark_run_service = BenchmarkRunService(
        chat_service,
        agent_runtime_service,
        history_repository,
    )
    training_corpus_service = TrainingCorpusService(knowledge_service)
    training_eval_service = TrainingEvalService(ollama_client)
    training_fine_tune_service = TrainingFineTuneService(training_corpus_service)
    return CliRuntime(
        knowledge_service=knowledge_service,
        retrieval_service=retrieval_service,
        directory_analysis_service=directory_analysis_service,
        answer_service=answer_service,
        ollama_client=ollama_client,
        history_repository=history_repository,
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

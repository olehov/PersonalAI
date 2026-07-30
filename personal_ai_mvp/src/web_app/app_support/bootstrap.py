"""Bootstrap helpers for the PersonalAI web application."""

from __future__ import annotations

from pathlib import Path

from application.agent_runtime.service import AgentRuntimeService
from application.chat.preprocessor import PromptPreprocessor
from application.chat.routing import RequestRoutingService
from application.chat.service import ChatService
from application.knowledge.answer_service import AnswerService
from application.knowledge.directory_analysis_service import DirectoryAnalysisService
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.notes.draft_service import NoteDraftService
from application.notes.mutation_service import NoteMutationService
from application.notes.policy import NotePolicy
from infrastructure.llm.ollama_client import OllamaClient
from infrastructure.llm.openai_responses_client import OpenAIResponsesClient
from infrastructure.history.repository import SQLiteQueryHistoryRepository
from infrastructure.llm.routing_model_client import RoutingModelClient


def build_runtime_components(
    *,
    vault_root: Path,
    settings,
    ollama_base_url: str | None = None,
    ollama_timeout_seconds: int | None = None,
) -> dict[str, object]:
    knowledge = KnowledgeService(vault_root)
    knowledge.load()

    retrieval = RetrievalService(knowledge)
    directory_analysis = DirectoryAnalysisService(knowledge)
    router = RequestRoutingService()
    answer_service = AnswerService(retrieval)

    ollama_client = OllamaClient(
        base_url=ollama_base_url or settings.ollama_base_url,
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
    prompt_preprocessor = PromptPreprocessor(
        mode=settings.prompt_preprocessor_mode,
        model_client=model_client,
        translation_model=settings.prompt_translation_model,
        fallback_translation_model=settings.prompt_translation_fallback_model,
    )
    history_repository = SQLiteQueryHistoryRepository(
        settings.history_db_path(vault_root)
    )
    mutation_service = NoteMutationService(knowledge, NotePolicy(vault_root))
    chat = ChatService(answer_service, model_client, history_repository)
    agent_runtime = AgentRuntimeService(
        knowledge,
        answer_service,
        model_client,
        history_repository,
    )
    drafts = NoteDraftService(answer_service, mutation_service, model_client)

    return {
        "knowledge": knowledge,
        "directory_analysis": directory_analysis,
        "router": router,
        "ollama_client": model_client,
        "prompt_preprocessor": prompt_preprocessor,
        "history_repository": history_repository,
        "chat": chat,
        "agent_runtime": agent_runtime,
        "drafts": drafts,
    }

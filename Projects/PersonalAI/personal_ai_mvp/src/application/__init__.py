"""Small public facade for top-level PersonalAI application services.

Internal code should import directly from canonical feature packages such as
`application.chat`, `application.knowledge`, `application.notes`,
`application.training`, `application.benchmark`, and `application.agent_runtime`.
"""

from application.agent_runtime.service import AgentRuntimeService
from application.agent_runtime.tool_registry import AgentToolContext, AgentToolRegistry
from application.benchmark.pack_service import BenchmarkPackService
from application.benchmark.run_service import BenchmarkCompareResult, BenchmarkRunService
from application.chat.preprocessor import PromptPreprocessResult, PromptPreprocessor
from application.chat.query_mapping import normalize_knowledge_query
from application.chat.routing import RequestRoutingService, WorkflowRouteDecision
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

__all__ = [
    "AgentRuntimeService",
    "AgentToolContext",
    "AgentToolRegistry",
    "AnswerService",
    "BenchmarkCompareResult",
    "BenchmarkPackService",
    "BenchmarkRunService",
    "ChatService",
    "DirectoryAnalysisService",
    "KnowledgeMaintenanceService",
    "KnowledgeService",
    "NoteDraftService",
    "NoteMutationService",
    "NotePolicy",
    "PromptPreprocessResult",
    "PromptPreprocessor",
    "RequestRoutingService",
    "RetrievalService",
    "TrainingCorpusService",
    "TrainingEvalService",
    "TrainingFineTuneService",
    "WorkflowRouteDecision",
    "normalize_knowledge_query",
]

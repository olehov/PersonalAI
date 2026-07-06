from __future__ import annotations

from pathlib import Path

from personal_ai.application.answer_service import AnswerService
from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.retrieval_service import RetrievalService
from personal_ai.domain.models import AgentRuntimeArtifact, GeneratedAnswer
from personal_ai.web_ui import DEFAULT_UI_MODEL, PersonalAIWebApp


def build_app(root: Path) -> PersonalAIWebApp:
    return PersonalAIWebApp(vault_root=root)


def seed_ask_history(app: PersonalAIWebApp, root: Path) -> None:
    knowledge = KnowledgeService(root)
    knowledge.load()
    prompt = AnswerService(RetrievalService(knowledge)).prepare_answer(
        "implement shell parser"
    )
    app._history_repository.save_generated_answer(
        GeneratedAnswer(
            model=DEFAULT_UI_MODEL,
            question="implement shell parser",
            answer_text="Architecture\nModules\nExecution Flow",
            citations=prompt.citations,
            prompt=prompt,
        ),
        scope_dirs=("Projects",),
        latency_ms=15,
    )


def seed_agent_history(app: PersonalAIWebApp) -> int:
    saved = app._history_repository.save_agent_runtime_artifact(
        AgentRuntimeArtifact(
            model="deepseek-r1:8b",
            request_text="build minishell",
            normalized_goal="build minishell",
            task_mode="implementation",
            status="needs_execution_layer",
            scope_dirs=("Projects",),
            citations=("Projects/Minishell.md",),
            steps=(),
            final_output="Goal\nConstraints",
        ),
        latency_ms=42,
    )
    return saved.entry_id

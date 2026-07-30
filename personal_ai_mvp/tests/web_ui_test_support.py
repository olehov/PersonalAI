from __future__ import annotations

from pathlib import Path

from application.knowledge.answer_service import AnswerService
from application.benchmark.run_service import BenchmarkRunResult
from application.knowledge.knowledge_service import KnowledgeService
from application.chat.preprocessor import PromptPreprocessor
from application.knowledge.retrieval_service import RetrievalService
from domain.models import AgentRuntimeArtifact, GeneratedAnswer
from web_app.app import DEFAULT_UI_MODEL, PersonalAIWebApp


def build_app(root: Path) -> PersonalAIWebApp:
    app = PersonalAIWebApp(vault_root=root)
    app._prompt_preprocessor = PromptPreprocessor(mode="disabled")  # type: ignore[attr-defined]
    return app


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


def seed_benchmark_history(app: PersonalAIWebApp) -> int:
    saved = app._history_repository.save_benchmark_run_result(
        BenchmarkRunResult(
            pack_id="repo-aware-v1",
            task_id="multi-turn-bsq-c-continuation",
            category="multi_turn_continuation",
            workflow="ask",
            model="gpt-oss:20b",
            status="completed",
            scope_dirs=("Projects", "Languages/C"),
            prompt_text="Implement BSQ in C incrementally and continue from prior steps.",
            latency_ms=83,
            result_payload={
                "multi_turn": True,
                "turn_count": 2,
                "final_status": "completed",
                "final_payload": {
                    "answer_text": "Completed final BSQ slice.",
                },
                "turn_results": [
                    {
                        "turn_index": 1,
                        "prompt": "Create the initial BSQ file tree.",
                        "status": "completed",
                        "result_payload": {
                            "answer_text": "Drafted tree and parser entrypoint.",
                        },
                    },
                    {
                        "turn_index": 2,
                        "prompt": "Continue and finish the implementation.",
                        "status": "completed",
                        "result_payload": {
                            "answer_text": "Completed DP core and validation.",
                        },
                    },
                ],
            },
        )
    )
    return saved.entry_id

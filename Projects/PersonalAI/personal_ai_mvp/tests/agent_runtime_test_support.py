from __future__ import annotations

import unittest
from pathlib import Path

from personal_ai.application.agent_runtime_service import AgentRuntimeService
from personal_ai.application.answer_service import AnswerService
from personal_ai.application.knowledge_service import (
    KnowledgeService,
    serialize_agent_runtime_artifact,
)
from personal_ai.application.retrieval_service import RetrievalService
from personal_ai.domain.models import PromptMessage


class FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[PromptMessage, ...], dict[str, object] | None]] = []

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        return self.chat_with_options(model=model, messages=messages, options=None)

    def chat_with_options(
        self,
        *,
        model: str,
        messages: tuple[PromptMessage, ...],
        options: dict[str, object] | None = None,
    ) -> str:
        self.calls.append((model, messages, options))
        user_prompt = messages[-1].content
        if "Recursive Planning Critique:" in user_prompt:
            return (
                "Strengths\n- The slice is parser-focused.\n\n"
                "Issues\n- Validation is too vague.\n\n"
                "Missing Grounding\n- Needs explicit file references.\n\n"
                "Better First Slice\n- Keep the parser stub narrow.\n\n"
                "Improve\n- Tighten files and validation."
            )
        if "Recursive Planning Final Pass:" in user_prompt:
            return (
                "Goal\nRefined goal.\n\n"
                "Constraints\nStay within the first parser slice.\n\n"
                "Existing Context\nGrounded note and repo summary available.\n\n"
                "Modules\nsrc/parser.c, include/minishell.h.\n\n"
                "Incremental Slices\n1. Parser stub.\n2. Token integration.\n3. Executor wiring.\n\n"
                "First Slice\nAdd a parser entrypoint stub only.\n\n"
                "First Actions\n1. Edit src/parser.c.\n2. Update include/minishell.h.\n\n"
                "Validation\n1. make all\n2. make clean\n\n"
                "Runtime Limits\nPlan artifact only; no files mutated."
            )
        if "Patch Planning Contract:" in user_prompt:
            return (
                "Scope\nFirst parser slice only.\n\n"
                "Files\n- src/parser.c\n- include/minishell.h\n\n"
                "Edits\n- Add parser entrypoint stub in src/parser.c.\n"
                "- Declare the parser interface in include/minishell.h.\n\n"
                "Risks\n- Keep parser state minimal to avoid blocking later tokenizer work.\n\n"
                "Validation Order\n1. Build with make.\n2. Confirm new symbols are wired cleanly."
            )
        if "Module Draft Contract:" in user_prompt:
            return (
                "Target\nsrc/parser.c\n\nIntent\nCreate the first parser slice.\n\n"
                "Draft\n```c\nint parse_tokens(void) {\n    return 0;\n}\n```\n\n"
                "Integration Notes\nWire into the shell loop later.\n\n"
                "Validation Notes\nCompile the first slice with make."
            )
        if "Scaffold Tree Contract:" in user_prompt:
            if "helper module" in user_prompt.casefold():
                return (
                    '{'
                    '"dirs":["runtime_scaffold","runtime_scaffold/src"],'
                    '"source_groups":['
                    '{"name":"helpers","dir":"runtime_scaffold/src","files":['
                    '{"path":"runtime_scaffold/src/helpers.py","purpose":"Reusable helper functions for the first slice."}'
                    "]}]}"
                )
            if "minishell" in user_prompt.casefold():
                return (
                    '{'
                    '"dirs":['
                    '"runtime_scaffold",'
                    '"runtime_scaffold/include",'
                    '"runtime_scaffold/src",'
                    '"runtime_scaffold/src/parser",'
                    '"runtime_scaffold/src/executor",'
                    '"runtime_scaffold/src/builtins"'
                    '],'
                    '"root_files":['
                    '{"path":"runtime_scaffold/Makefile","purpose":"Build the minishell target from modular C sources."}'
                    '],'
                    '"include_files":['
                    '{"path":"runtime_scaffold/include/minishell.h","purpose":"Shared shell interfaces."}'
                    '],'
                    '"source_groups":['
                    '{"name":"entry","dir":"runtime_scaffold/src","files":[{"path":"runtime_scaffold/src/main.c","purpose":"Program entrypoint."}]},'
                    '{"name":"parser","dir":"runtime_scaffold/src/parser","files":[{"path":"runtime_scaffold/src/parser/parser.c","purpose":"Parser implementation scaffold."}]},'
                    '{"name":"executor","dir":"runtime_scaffold/src/executor","files":[{"path":"runtime_scaffold/src/executor/exec.c","purpose":"execve execution scaffold."}]},'
                    '{"name":"builtins","dir":"runtime_scaffold/src/builtins","files":[{"path":"runtime_scaffold/src/builtins/builtins.c","purpose":"Builtin dispatch scaffold."}]}'
                    "]}"
                )
            return (
                '{'
                '"dirs":["runtime_scaffold"],'
                '"files":[{"path":"runtime_scaffold/generated_scaffold.py","purpose":"Starter scaffold file."}]'
                "}"
            )
        if "Scaffold File Contract:" in user_prompt:
            if "helper module" in user_prompt.casefold() or "helpers.py" in user_prompt.casefold():
                return (
                    "```python\n"
                    '"""Generated helper scaffold."""\n\n'
                    "from __future__ import annotations\n\n"
                    "def normalize_text(value: str) -> str:\n"
                    '    """Return a trimmed single-line representation."""\n'
                    '    return " ".join(value.strip().split())\n'
                    "```\n"
                )
            return (
                "```python\n"
                '"""Generated scaffold file."""\n\n'
                "from __future__ import annotations\n\n"
                "def main() -> int:\n"
                "    return 0\n"
                "```\n"
            )
        return (
            "Goal\nConstraints\nExisting Context\nModules\nIncremental Slices\n"
            "First Slice\nFirst Actions\nValidation\nRuntime Limits"
        )


class FakeAgentHistoryRepository:
    def __init__(self) -> None:
        self.saved: list[dict[str, object]] = []

    def save_agent_runtime_artifact(self, artifact, *, latency_ms=None) -> None:
        self.saved.append(
            {
                "request_text": artifact.request_text,
                "model": artifact.model,
                "status": artifact.status,
                "latency_ms": latency_ms,
            }
        )


class AgentRuntimeServiceTestSupport(unittest.TestCase):
    def _build_service(
        self,
        root: Path,
        *,
        fake_client: FakeOllamaClient | None = None,
        history_repository=None,
        recursive_refinement_enabled: bool | None = None,
    ) -> tuple[FakeOllamaClient, AgentRuntimeService]:
        knowledge = KnowledgeService(root)
        knowledge.load()
        client = fake_client or FakeOllamaClient()
        service = AgentRuntimeService(
            knowledge,
            AnswerService(RetrievalService(knowledge)),
            client,
            history_repository,
            recursive_refinement_enabled=recursive_refinement_enabled,
        )
        return client, service

    def _run_payload(
        self,
        service: AgentRuntimeService,
        request_text: str,
        *,
        model: str,
        scope_dirs: tuple[str, ...] = (),
        conversation_history: tuple[PromptMessage, ...] = (),
        reasoning_mode: str = "standard",
    ) -> dict[str, object]:
        artifact = service.run(
            request_text,
            model=model,
            scope_dirs=scope_dirs,
            conversation_history=conversation_history,
            reasoning_mode=reasoning_mode,
        )
        return serialize_agent_runtime_artifact(artifact)

    def _executions_by_type(
        self,
        payload: dict[str, object],
    ) -> dict[str, dict[str, object]]:
        return {item["action_type"]: item for item in payload["action_executions"]}

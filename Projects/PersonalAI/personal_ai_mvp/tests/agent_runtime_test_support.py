from __future__ import annotations

import unittest
from pathlib import Path

from application.agent_runtime.service import AgentRuntimeService
from application.knowledge.answer_service import AnswerService
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.shared.serializers import serialize_agent_runtime_artifact
from domain.models import PromptMessage
from tests.path_test_support import scaffold_path


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
        scaffold_root = scaffold_path()
        include_dir = scaffold_path("include")
        src_dir = scaffold_path("src")
        parser_dir = scaffold_path("src", "parser")
        executor_dir = scaffold_path("src", "executor")
        builtins_dir = scaffold_path("src", "builtins")
        makefile_path = scaffold_path("Makefile")
        minishell_header_path = scaffold_path("include", "minishell.h")
        main_c_path = scaffold_path("src", "main.c")
        parser_c_path = scaffold_path("src", "parser", "parser.c")
        exec_c_path = scaffold_path("src", "executor", "exec.c")
        builtins_c_path = scaffold_path("src", "builtins", "builtins.c")
        generated_scaffold_path = scaffold_path("generated_scaffold.py")
        helpers_py_path = scaffold_path("src", "helpers.py")
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
        if "Planning Approval Review:" in user_prompt:
            if "Tighten files and validation" in user_prompt:
                return "NEEDS_REVISION\n- tighten the first slice further\n- make the first actions more concrete"
            return "APPROVED\n- grounded enough for executor handoff"
        if "Executor Artifact Critique:" in user_prompt:
            return (
                "- missing grounding: add exact target files when possible\n"
                "- misleading claims: keep this as a draft only\n"
                "- structure: tighten the first slice and validation wording\n"
                "- best improvement: return a more concrete artifact with explicit files"
            )
        if "Executor Approval Review:" in user_prompt:
            if "Target\nsrc/parser.c" in user_prompt or "Files\n- src/parser.c" in user_prompt:
                return "APPROVED\n- artifact is concrete enough"
            return "NEEDS_REVISION\n- make target files more explicit"
        if "Executor Artifact Final Pass:" in user_prompt:
            if "Artifact Kind: module_draft" in user_prompt:
                return (
                    "Target\nsrc/parser.c\n\nIntent\nCreate the first parser slice.\n\n"
                    "Draft\n```c\nint parse_tokens(void) {\n    return 0;\n}\n```\n\n"
                    "Integration Notes\nWire into the shell loop later.\n\n"
                    "Validation Notes\nCompile the first slice with make."
                )
            if "Artifact Kind: patch_plan" in user_prompt:
                return (
                    "Scope\nFirst parser slice only.\n\n"
                    "Files\n- src/parser.c\n- include/minishell.h\n\n"
                    "Edits\n- Add parser entrypoint stub in src/parser.c.\n"
                    "- Declare the parser interface in include/minishell.h.\n\n"
                    "Risks\n- Keep parser state minimal to avoid blocking later tokenizer work.\n\n"
                    "Validation Order\n1. Build with make.\n2. Confirm new symbols are wired cleanly."
                )
            if "Artifact Kind: scaffold_tree_manifest" in user_prompt:
                if "minishell" in user_prompt.casefold():
                    return (
                        '{'
                        '"dirs":['
                        f'"{scaffold_root}",'
                        f'"{include_dir}",'
                        f'"{src_dir}",'
                        f'"{parser_dir}",'
                        f'"{executor_dir}",'
                        f'"{builtins_dir}"'
                        '],'
                        '"root_files":['
                        f'{{"path":"{makefile_path}","purpose":"Build the minishell target from modular C sources."}}'
                        '],'
                        '"include_files":['
                        f'{{"path":"{minishell_header_path}","purpose":"Shared shell interfaces."}}'
                        '],'
                        '"source_groups":['
                        f'{{"name":"entry","dir":"{src_dir}","files":[{{"path":"{main_c_path}","purpose":"Program entrypoint."}}]}},'
                        f'{{"name":"parser","dir":"{parser_dir}","files":[{{"path":"{parser_c_path}","purpose":"Parser implementation scaffold."}}]}},'
                        f'{{"name":"executor","dir":"{executor_dir}","files":[{{"path":"{exec_c_path}","purpose":"execve execution scaffold."}}]}},'
                        f'{{"name":"builtins","dir":"{builtins_dir}","files":[{{"path":"{builtins_c_path}","purpose":"Builtin dispatch scaffold."}}]}}'
                        "]}"
                    )
                return (
                    '{'
                    f'"dirs":["{scaffold_root}"],'
                    f'"files":[{{"path":"{generated_scaffold_path}","purpose":"Starter scaffold file."}}]'
                    "}"
                )
            if "Artifact Kind: scaffold_file" in user_prompt:
                if "helper module" in user_prompt.casefold() or "helpers.py" in user_prompt.casefold():
                    return (
                        '"""Generated helper scaffold."""\n\n'
                        "from __future__ import annotations\n\n"
                        "def normalize_text(value: str) -> str:\n"
                        '    """Return a trimmed single-line representation."""\n'
                        '    return " ".join(value.strip().split())\n'
                    )
                return (
                    '"""Generated scaffold file."""\n\n'
                    "from __future__ import annotations\n\n"
                    "def main() -> int:\n"
                    "    return 0\n"
                )
            return "Executor refinement fallback."
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
                    f'"dirs":["{scaffold_root}","{src_dir}"],'
                    '"source_groups":['
                    f'{{"name":"helpers","dir":"{src_dir}","files":['
                    f'{{"path":"{helpers_py_path}","purpose":"Reusable helper functions for the first slice."}}'
                    "]}]}"
                )
            if "minishell" in user_prompt.casefold():
                return (
                    '{'
                    '"dirs":['
                    f'"{scaffold_root}",'
                    f'"{include_dir}",'
                    f'"{src_dir}",'
                    f'"{parser_dir}",'
                    f'"{executor_dir}",'
                    f'"{builtins_dir}"'
                    '],'
                    '"root_files":['
                    f'{{"path":"{makefile_path}","purpose":"Build the minishell target from modular C sources."}}'
                    '],'
                    '"include_files":['
                    f'{{"path":"{minishell_header_path}","purpose":"Shared shell interfaces."}}'
                    '],'
                    '"source_groups":['
                    f'{{"name":"entry","dir":"{src_dir}","files":[{{"path":"{main_c_path}","purpose":"Program entrypoint."}}]}},'
                    f'{{"name":"parser","dir":"{parser_dir}","files":[{{"path":"{parser_c_path}","purpose":"Parser implementation scaffold."}}]}},'
                    f'{{"name":"executor","dir":"{executor_dir}","files":[{{"path":"{exec_c_path}","purpose":"execve execution scaffold."}}]}},'
                    f'{{"name":"builtins","dir":"{builtins_dir}","files":[{{"path":"{builtins_c_path}","purpose":"Builtin dispatch scaffold."}}]}}'
                    "]}"
                )
            return (
                '{'
                f'"dirs":["{scaffold_root}"],'
                f'"files":[{{"path":"{generated_scaffold_path}","purpose":"Starter scaffold file."}}]'
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

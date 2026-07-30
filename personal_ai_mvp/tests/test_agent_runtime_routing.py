from __future__ import annotations

import tempfile
from pathlib import Path

from tests.agent_runtime_test_support import AgentRuntimeServiceTestSupport


class AgentRuntimeRoutingTests(AgentRuntimeServiceTestSupport):
    def test_run_normalizes_goal_from_long_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Shell.md").write_text(
                "# Shell\nBuild parser and executor.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            artifact = service.run(
                (
                    "You are working inside my local project folder.\n"
                    "Your task is to build the mandatory part of 42 minishell.\n"
                    "Keep going until it compiles."
                ),
                model="gemma:latest",
            )

            self.assertEqual(
                artifact.normalized_goal,
                "Your task is to build the mandatory part of 42 minishell.",
            )

    def test_parse_planning_sections_accepts_markdown_headings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Shell.md").write_text(
                "# Shell\nParser and executor.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)

            sections = service._parse_planning_sections(
                "### Goal\nBuild parser slice.\n\n"
                "### Constraints\nStay narrow.\n\n"
                "### Existing Context\nRepo known.\n\n"
                "### Modules\nsrc/parser.c\n\n"
                "### Incremental Slices\n1. Parser stub\n2. Token wiring\n\n"
                "### First Slice\nEdit src/parser.c.\n\n"
                "### First Actions\n1. Edit src/parser.c\n\n"
                "### Validation\n1. make all\n\n"
                "### Runtime Limits\nPlan only.\n"
            )

            self.assertEqual(sections["goal"], "Build parser slice.")
            self.assertEqual(sections["first slice"], "Edit src/parser.c.")
            self.assertEqual(sections["validation"], "1. make all")

    def test_run_resolves_nested_repo_from_request_path_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "42" / "Minishell").mkdir(parents=True)
            (root / "Projects" / "42" / "Minishell" / "src").mkdir()
            (root / "Projects" / "42" / "Minishell" / "Makefile").write_text(
                "all:\n\tcc src/main.c\n",
                encoding="utf-8",
            )
            (root / "Projects" / "42 Minishell.md").write_text(
                "# 42 Minishell\nProject lives in Projects/42/Minishell.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect repository at Projects/42/Minishell and plan the first parser slice.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertEqual(
                executions_by_type["inspect_repo"]["target"],
                "Projects/42/Minishell",
            )

    def test_run_uses_citation_context_to_choose_matching_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "Minishell").mkdir(parents=True)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects" / "Minishell" / "src").mkdir()
            (root / "Projects" / "Minishell" / "Makefile").write_text(
                "all:\n\tcc src/main.c\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nNeed shell loop and parser.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI.md").write_text(
                "# PersonalAI\nLocal-first engineering agent.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Build the mandatory part of minishell with grounded steps.",
                model="deepseek-r1:8b",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertEqual(
                executions_by_type["inspect_repo"]["target"],
                "Projects/Minishell",
            )

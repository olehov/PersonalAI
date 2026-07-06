from __future__ import annotations

import os
import tempfile
from pathlib import Path

from tests.agent_runtime_test_support import (
    AgentRuntimeServiceTestSupport,
    FakeAgentHistoryRepository,
    FakeOllamaClient,
)


class AgentRuntimeProjectTests(AgentRuntimeServiceTestSupport):
    def test_run_builds_runtime_artifact_for_project_scale_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser, tokenizer, executor, and signals.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()
            (root / "Projects" / "Minishell" / "src").mkdir()
            (root / "Projects" / "Minishell" / "include").mkdir()
            (root / "Projects" / "Minishell" / "src" / "main.c").write_text(
                "int main(void) { return 0; }\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell" / "include" / "minishell.h").write_text(
                "#ifndef MINISHELL_H\n#define MINISHELL_H\n#endif\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell" / "Makefile").write_text(
                "all:\n\tcc src/main.c -o minishell\n\nclean:\n\trm -f minishell\n",
                encoding="utf-8",
            )

            fake_client, service = self._build_service(
                root,
                recursive_refinement_enabled=True,
            )

            payload = self._run_payload(
                service,
                "Your task is to build the mandatory part of 42 minishell.",
                model="deepseek-r1:8b",
                scope_dirs=("Projects",),
            )

            self.assertEqual(payload["model"], "deepseek-r1:8b")
            self.assertEqual(payload["executor_model"], "deepseek-r1:8b")
            self.assertEqual(payload["task_mode"], "implementation")
            self.assertEqual(payload["status"], "needs_execution_layer")
            self.assertEqual(len(payload["steps"]), 4)
            self.assertEqual(payload["steps"][0]["kind"], "retrieval")
            self.assertEqual(payload["steps"][1]["kind"], "planning")
            self.assertEqual(payload["steps"][2]["kind"], "action_plan")
            self.assertEqual(payload["steps"][3]["kind"], "action_execution")
            self.assertEqual(payload["overview"]["step_count"], 4)
            self.assertGreaterEqual(payload["overview"]["planned_task_count"], 1)
            self.assertGreaterEqual(payload["overview"]["recommended_action_count"], 6)
            self.assertGreaterEqual(payload["overview"]["failed_action_count"], 0)
            self.assertIsNotNone(payload["task_plan"])
            self.assertEqual(
                payload["task_plan"]["goal"],
                "Refined goal.",
            )
            self.assertIsNone(payload["discussion_preset"])
            self.assertEqual(payload["discussion_trace"]["preset"], "custom")
            self.assertIn("Refined goal.", payload["discussion_trace"]["synthesis_output"])
            self.assertEqual(payload["task_plan"]["entries"][0]["status"], "next")
            self.assertIn("Parser stub", payload["task_plan"]["entries"][0]["title"])
            self.assertIn(
                "No filesystem writes, shell commands, or tests were executed",
                payload["steps"][1]["observation"],
            )
            self.assertGreaterEqual(len(payload["recommended_actions"]), 6)
            self.assertEqual(payload["recommended_actions"][0]["action_type"], "inspect_note")
            self.assertEqual(payload["recommended_actions"][1]["action_type"], "inspect_repo")
            self.assertEqual(payload["recommended_actions"][2]["action_type"], "inspect_file_tree")
            self.assertEqual(payload["recommended_actions"][3]["action_type"], "inspect_build_config")
            self.assertEqual(payload["recommended_actions"][4]["action_type"], "inspect_target_files")
            self.assertEqual(payload["recommended_actions"][5]["action_type"], "draft_module")
            self.assertEqual(payload["recommended_actions"][6]["action_type"], "plan_patch")
            self.assertEqual(payload["recommended_actions"][8]["action_type"], "run_allowed_command")
            self.assertGreaterEqual(len(payload["action_executions"]), 7)
            executions_by_type = self._executions_by_type(payload)
            self.assertEqual(executions_by_type["inspect_note"]["status"], "executed")
            self.assertIn("title=Minishell", executions_by_type["inspect_note"]["output_text"])
            self.assertEqual(executions_by_type["inspect_repo"]["status"], "executed")
            self.assertIn("path=", executions_by_type["inspect_repo"]["output_text"])
            self.assertEqual(executions_by_type["inspect_file_tree"]["status"], "executed")
            self.assertIn("[dir] src", executions_by_type["inspect_file_tree"]["output_text"])
            self.assertIn("[file] minishell.h", executions_by_type["inspect_file_tree"]["output_text"])
            self.assertEqual(executions_by_type["inspect_build_config"]["status"], "executed")
            self.assertIn("manifest=Makefile", executions_by_type["inspect_build_config"]["output_text"])
            self.assertIn("targets=all", executions_by_type["inspect_build_config"]["output_text"])
            self.assertEqual(executions_by_type["plan_validation"]["status"], "executed")
            self.assertIn(
                "recommended_commands=make all; make clean",
                executions_by_type["plan_validation"]["output_text"],
            )
            self.assertIn("run_allowed_command", executions_by_type)
            self.assertIn(
                "path=Projects/Minishell/src/main.c",
                executions_by_type["inspect_target_files"]["output_text"],
            )
            self.assertEqual(executions_by_type["draft_module"]["status"], "executed")
            self.assertIn("saved_path=.personal_ai/agent_runtime_drafts/", executions_by_type["draft_module"]["output_text"])
            self.assertIn("Target", executions_by_type["draft_module"]["output_text"])
            self.assertIn("Draft", executions_by_type["draft_module"]["output_text"])
            self.assertEqual(executions_by_type["plan_patch"]["status"], "executed")
            self.assertIn("saved_path=.personal_ai/agent_runtime_drafts/", executions_by_type["plan_patch"]["output_text"])
            self.assertIn("Files", executions_by_type["plan_patch"]["output_text"])
            self.assertIn("src/parser.c", executions_by_type["plan_patch"]["output_text"])
            self.assertIn("Agent Runtime Contract:", fake_client.calls[0][1][1].content)
            self.assertIn(
                "Do not choose 'inspect', 'read', 'review', or 'analyze' as the only First Slice deliverable",
                fake_client.calls[0][1][1].content,
            )
            self.assertEqual(fake_client.calls[0][2], {"num_predict": 520})
            module_draft_prompt = next(
                messages[-1].content
                for _, messages, _ in fake_client.calls
                if "Module Draft Contract:" in messages[-1].content
            )
            self.assertIn("File Tree:", module_draft_prompt)
            self.assertIn("Build Config:", module_draft_prompt)
            self.assertIn("Suggested Files:", module_draft_prompt)
            self.assertIn("Related Files:", module_draft_prompt)
            self.assertIn("Target File Context:", module_draft_prompt)
            self.assertIn("Validation Baseline:", module_draft_prompt)
            self.assertIn("Planner Handoff:", module_draft_prompt)
            self.assertIn("chosen_first_slice=", module_draft_prompt)
            self.assertIn("target_files=", module_draft_prompt)
            self.assertIn("recommended_commands=make all; make clean", module_draft_prompt)
            self.assertIn("Projects/Minishell/src/main.c", module_draft_prompt)
            self.assertIn("int main(void) { return 0; }", module_draft_prompt)
            patch_plan_prompt = next(
                messages[-1].content
                for _, messages, _ in fake_client.calls
                if "Patch Planning Contract:" in messages[-1].content
            )
            self.assertIn("Build Config:", patch_plan_prompt)
            self.assertIn("Suggested Files:", patch_plan_prompt)
            self.assertIn("Related Files:", patch_plan_prompt)
            self.assertIn("Validation Baseline:", patch_plan_prompt)
            self.assertIn("recommended_commands=make all; make clean", patch_plan_prompt)
            self.assertIn(
                "Only safe in-process actions and whitelist validation commands were executed.",
                payload["steps"][3]["observation"],
            )

    def test_run_derives_python_validation_from_pyproject_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "tests").mkdir()
            (root / "Projects" / "PersonalAI" / "pyproject.toml").write_text(
                "[project]\nname = \"personal-ai\"\n\n[tool.pytest.ini_options]\naddopts = \"-q\"\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI.md").write_text(
                "# PersonalAI\nPython project with tests.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/PersonalAI and prepare the first implementation slice.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn(
                "sections=[project], [tool], [tool.pytest], [tool.pytest.ini_options]",
                executions_by_type["inspect_build_config"]["output_text"],
            )
            self.assertIn(
                "recommended_commands=python -m unittest discover -s tests; python -m pytest",
                executions_by_type["plan_validation"]["output_text"],
            )

    def test_run_derives_package_scripts_from_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "Frontend").mkdir(parents=True)
            (root / "Projects" / "Frontend" / "package.json").write_text(
                (
                    "{\n"
                    '  "name": "frontend",\n'
                    '  "scripts": {\n'
                    '    "build": "vite build",\n'
                    '    "test": "vitest run",\n'
                    '    "lint": "eslint ."\n'
                    "  }\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            (root / "Projects" / "Frontend.md").write_text(
                "# Frontend\nJS project.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/Frontend and plan the first UI slice.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn(
                "scripts=build, test, lint",
                executions_by_type["inspect_build_config"]["output_text"],
            )
            self.assertIn(
                "recommended_commands=npm run test; npm run build; npm run lint",
                executions_by_type["plan_validation"]["output_text"],
            )

    def test_run_uses_exact_scoped_project_root_and_drafts_first_slice_for_python_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = (
                root
                / "Projects"
                / "PersonalAI"
                / "personal_ai_mvp"
                / "training_examples"
                / "benchmark_projects"
                / "python_task_cli"
            )
            (project_root / "src" / "task_cli").mkdir(parents=True)
            (project_root / "tests").mkdir()
            (project_root / "pyproject.toml").write_text(
                (
                    "[project]\n"
                    'name = "python-task-cli"\n'
                    "\n"
                    "[tool.pytest.ini_options]\n"
                    'testpaths = ["tests"]\n'
                ),
                encoding="utf-8",
            )
            (project_root / "README.md").write_text(
                "# Python Task CLI\n"
                "- keep the first implementation slice narrow\n"
                "- add a `done` command\n"
                "- inspect `src/task_cli/store.py`\n"
                "- inspect `src/task_cli/cli.py`\n",
                encoding="utf-8",
            )
            (project_root / "src" / "task_cli" / "__init__.py").write_text(
                '"""Task CLI."""\n',
                encoding="utf-8",
            )
            (project_root / "src" / "task_cli" / "cli.py").write_text(
                "def main():\n    return 0\n",
                encoding="utf-8",
            )
            (project_root / "src" / "task_cli" / "store.py").write_text(
                "class TaskStore:\n    pass\n",
                encoding="utf-8",
            )
            (project_root / "tests" / "test_cli.py").write_text(
                "def test_placeholder():\n    assert True\n",
                encoding="utf-8",
            )

            fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                (
                    "Inspect repository at "
                    "`Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli`.\n"
                    "Add a done command and draft the safest first slice."
                ),
                model="gemma:latest",
                scope_dirs=(
                    "Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli",
                ),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn(
                "draft_module",
                [item["action_type"] for item in payload["recommended_actions"]],
            )
            self.assertIn(
                "inspect_target_files",
                [item["action_type"] for item in payload["recommended_actions"]],
            )
            self.assertEqual(
                executions_by_type["inspect_repo"]["target"],
                "Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli",
            )
            self.assertIn(
                "manifest=pyproject.toml",
                executions_by_type["inspect_build_config"]["output_text"],
            )
            self.assertIn(
                "test_framework_hints=pytest_style",
                executions_by_type["inspect_build_config"]["output_text"],
            )
            self.assertIn(
                "recommended_commands=python -m pytest; python -m unittest discover -s tests",
                executions_by_type["plan_validation"]["output_text"],
            )
            self.assertEqual(executions_by_type["inspect_target_files"]["status"], "executed")
            self.assertIn(
                "path=Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli/src/task_cli/store.py",
                executions_by_type["inspect_target_files"]["output_text"],
            )
            self.assertIn("class TaskStore:", executions_by_type["inspect_target_files"]["output_text"])
            self.assertNotIn(
                "path=projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli/src/task_cli/store.py",
                executions_by_type["inspect_target_files"]["output_text"],
            )
            self.assertEqual(executions_by_type["draft_module"]["status"], "executed")
            self.assertIn("saved_path=.personal_ai/agent_runtime_drafts/", executions_by_type["draft_module"]["output_text"])
            self.assertIn("Draft", executions_by_type["draft_module"]["output_text"])
            module_draft_prompt = next(
                messages[-1].content
                for _, messages, _ in fake_client.calls
                if "Module Draft Contract:" in messages[-1].content
            )
            self.assertIn("Planner Handoff:", module_draft_prompt)
            self.assertIn("Target File Context:", module_draft_prompt)
            self.assertIn("class TaskStore:", module_draft_prompt)
            self.assertIn(
                "Treat Target File Context, Suggested Files, and Related Files as the authoritative source",
                module_draft_prompt,
            )
            self.assertIn(
                "must_not_do=do not claim files were changed or tests were run; do not invent new repository structure when existing modules already fit",
                module_draft_prompt,
            )
            planning_prompt = fake_client.calls[0][1][1].content
            self.assertIn("File Tree:", planning_prompt)
            self.assertIn("Build Config:", planning_prompt)
            self.assertIn("Suggested Files:", planning_prompt)
            self.assertIn("Target File Context:", planning_prompt)
            self.assertIn(
                "Treat Repo Summary, File Tree, Suggested Files, and Target File Context as the authoritative source",
                planning_prompt,
            )
            self.assertIn(
                "Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli/src/task_cli/store.py",
                planning_prompt,
            )
            self.assertIn(
                "Projects/PersonalAI/personal_ai_mvp/training_examples/benchmark_projects/python_task_cli/src/task_cli/cli.py",
                planning_prompt,
            )
            self.assertIn("class TaskStore:", planning_prompt)
            self.assertIn("def main():", planning_prompt)
            self.assertIn("run_allowed_command", [item["action_type"] for item in payload["recommended_actions"]])

    def test_run_executes_whitelist_python_validation_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "SandboxPython"
            (project_root / "tests").mkdir(parents=True)
            (project_root / "pyproject.toml").write_text(
                "[project]\nname = \"sandbox-python\"\n",
                encoding="utf-8",
            )
            (project_root / "tests" / "test_basic.py").write_text(
                "import unittest\n\n"
                "class BasicTests(unittest.TestCase):\n"
                "    def test_truth(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (root / "Projects" / "SandboxPython.md").write_text(
                "# SandboxPython\nSmall Python project.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/SandboxPython and prepare the first implementation slice.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn("run_allowed_command", executions_by_type)
            self.assertEqual(executions_by_type["run_allowed_command"]["status"], "executed")
            self.assertIn(
                "command=python -m unittest discover -s tests",
                executions_by_type["run_allowed_command"]["output_text"],
            )
            self.assertIn("exit_code=0", executions_by_type["run_allowed_command"]["output_text"])

    def test_run_can_create_safe_repo_directory_and_file_for_write_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "ProbeProject"
            (project_root / "src").mkdir(parents=True)
            (project_root / "pyproject.toml").write_text(
                "[project]\nname = \"probe-project\"\n",
                encoding="utf-8",
            )
            (root / "Projects" / "ProbeProject.md").write_text(
                "# ProbeProject\nUse this project for runtime write probes.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/ProbeProject and create a safe scaffold directory and create file write probe.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn("create_dir", executions_by_type)
            self.assertIn("create_file", executions_by_type)
            self.assertEqual(executions_by_type["create_dir"]["status"], "executed")
            self.assertEqual(executions_by_type["create_file"]["status"], "executed")
            self.assertIn(
                "created_dir=runtime_write_probe",
                executions_by_type["create_dir"]["output_text"],
            )
            self.assertIn(
                "created_file=runtime_write_probe/WRITE_PROBE.md",
                executions_by_type["create_file"]["output_text"],
            )
            created_dir = project_root / "runtime_write_probe"
            created_file = created_dir / "WRITE_PROBE.md"
            self.assertTrue(created_dir.is_dir())
            self.assertTrue(created_file.is_file())
            self.assertIn(
                "created_by=safe_agent_runtime",
                created_file.read_text(encoding="utf-8"),
            )

    def test_run_can_create_safe_scaffold_file_with_generated_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "ScaffoldProject"
            (project_root / "src").mkdir(parents=True)
            (project_root / "tests").mkdir()
            (project_root / "pyproject.toml").write_text(
                "[project]\nname = \"scaffold-project\"\n",
                encoding="utf-8",
            )
            (project_root / "tests" / "test_basic.py").write_text(
                "import unittest\n\n"
                "class BasicTests(unittest.TestCase):\n"
                "    def test_truth(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (root / "Projects" / "ScaffoldProject.md").write_text(
                "# ScaffoldProject\nUse this project for scaffold-file generation.\n",
                encoding="utf-8",
            )

            fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/ScaffoldProject and create a scaffold file for a Python helper module.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn("create_scaffold_tree", executions_by_type)
            self.assertEqual(executions_by_type["create_scaffold_tree"]["status"], "executed")
            created_file = project_root / "runtime_scaffold" / "src" / "helpers.py"
            self.assertTrue(created_file.is_file())
            content = created_file.read_text(encoding="utf-8")
            self.assertIn("def normalize_text", content)
            self.assertNotIn("```", content)
            self.assertNotIn("import unittest", content)
            self.assertNotIn("from personal_ai.cli import main", content)
            self.assertIn(
                "created_file_count=1",
                executions_by_type["create_scaffold_tree"]["output_text"],
            )
            self.assertTrue(
                any("Scaffold Tree Contract:" in messages[-1].content for _, messages, _ in fake_client.calls)
            )
            scaffold_tree_prompt = next(
                messages[-1].content
                for _, messages, _ in fake_client.calls
                if "Scaffold Tree Contract:" in messages[-1].content
            )
            self.assertIn("Preferred schema:", scaffold_tree_prompt)

    def test_run_falls_back_when_helper_scaffold_looks_like_cli_or_stateful_module(self) -> None:
        class BadHelperScaffoldClient(FakeOllamaClient):
            def chat_with_options(
                self,
                *,
                model: str,
                messages,
                options=None,
            ) -> str:
                user_prompt = messages[-1].content
                if "Scaffold File Contract:" in user_prompt:
                    return (
                        "import argparse\n\n"
                        "class TaskStore:\n"
                        "    pass\n\n"
                        "if __name__ == '__main__':\n"
                        "    raise SystemExit(0)\n"
                    )
                return super().chat_with_options(
                    model=model,
                    messages=messages,
                    options=options,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "FallbackScaffoldProject"
            (project_root / "src").mkdir(parents=True)
            (project_root / "pyproject.toml").write_text(
                "[project]\nname = \"fallback-scaffold-project\"\n",
                encoding="utf-8",
            )
            (root / "Projects" / "FallbackScaffoldProject.md").write_text(
                "# FallbackScaffoldProject\nUse this project to validate helper scaffold fallback.\n",
                encoding="utf-8",
            )

            fake_client, service = self._build_service(
                root,
                fake_client=BadHelperScaffoldClient(),
            )
            payload = self._run_payload(
                service,
                "Inspect Projects/FallbackScaffoldProject and create a scaffold file for a Python helper module.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertEqual(executions_by_type["create_scaffold_tree"]["status"], "executed")
            created_file = project_root / "runtime_scaffold" / "src" / "helpers.py"
            self.assertTrue(created_file.is_file())
            content = created_file.read_text(encoding="utf-8")
            self.assertIn("def normalize_text", content)
            self.assertNotIn("class TaskStore", content)
            self.assertNotIn("argparse", content)
            self.assertNotIn("if __name__ ==", content)

    def test_run_can_create_multi_file_scaffold_tree_for_c_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "MiniShellStructure"
            project_root.mkdir(parents=True)
            (root / "Projects" / "MiniShellStructure.md").write_text(
                "# MiniShellStructure\nUse this project to validate multi-file scaffold tree generation.\n",
                encoding="utf-8",
            )

            fake_client, service = self._build_service(root)
            payload = self._run_payload(
                service,
                "Inspect Projects/MiniShellStructure and create a scaffold tree for the mandatory part of minishell.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertIn("create_scaffold_tree", executions_by_type)
            self.assertEqual(executions_by_type["create_scaffold_tree"]["status"], "executed")
            scaffold_root = project_root / "runtime_scaffold"
            self.assertTrue((scaffold_root / "include").is_dir())
            self.assertTrue((scaffold_root / "src" / "parser").is_dir())
            self.assertTrue((scaffold_root / "src" / "executor").is_dir())
            self.assertTrue((scaffold_root / "src" / "builtins").is_dir())
            self.assertTrue((scaffold_root / "Makefile").is_file())
            self.assertTrue((scaffold_root / "include" / "minishell.h").is_file())
            self.assertTrue((scaffold_root / "src" / "main.c").is_file())
            self.assertTrue((scaffold_root / "src" / "parser" / "parser.c").is_file())
            self.assertIn(
                "created_dir_count=6",
                executions_by_type["create_scaffold_tree"]["output_text"],
            )
            self.assertIn(
                "created_file_count=6",
                executions_by_type["create_scaffold_tree"]["output_text"],
            )
            self.assertIn(
                "runtime_scaffold/src/parser/parser.c",
                executions_by_type["create_scaffold_tree"]["output_text"],
            )
            self.assertTrue(
                any("Scaffold Tree Contract:" in messages[-1].content for _, messages, _ in fake_client.calls)
            )
            file_prompt = next(
                messages[-1].content
                for _, messages, _ in fake_client.calls
                if "Scaffold File Contract:" in messages[-1].content
                and "Target Path: runtime_scaffold/src/parser/parser.c" in messages[-1].content
            )
            self.assertIn("Scaffold Context:", file_prompt)
            self.assertIn("target_group=parser", file_prompt)
            self.assertIn("declared_headers=runtime_scaffold/include/minishell.h", file_prompt)

    def test_run_repairs_scaffold_file_with_missing_internal_include(self) -> None:
        class BrokenIncludeTreeClient(FakeOllamaClient):
            def chat_with_options(
                self,
                *,
                model: str,
                messages,
                options=None,
            ) -> str:
                user_prompt = messages[-1].content
                if "Scaffold Tree Contract:" in user_prompt:
                    return (
                        '{'
                        '"dirs":["runtime_scaffold","runtime_scaffold/src/parser"],'
                        '"files":['
                        '{"path":"runtime_scaffold/src/parser/parser.c","purpose":"Parser implementation scaffold."}'
                        "]}"
                    )
                if "Scaffold File Contract:" in user_prompt and "parser.c" in user_prompt:
                    return (
                        '#include "proto.h"\n\n'
                        "int parse_command(void)\n"
                        "{\n"
                        "    return 0;\n"
                        "}\n"
                    )
                return super().chat_with_options(
                    model=model,
                    messages=messages,
                    options=options,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "BrokenIncludeProject"
            project_root.mkdir(parents=True)
            (root / "Projects" / "BrokenIncludeProject.md").write_text(
                "# BrokenIncludeProject\nUse this project to validate scaffold dependency repair.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(
                root,
                fake_client=BrokenIncludeTreeClient(),
            )
            payload = self._run_payload(
                service,
                "Inspect Projects/BrokenIncludeProject and create a scaffold tree for a C parser module.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertEqual(executions_by_type["create_scaffold_tree"]["status"], "executed")
            self.assertIn(
                "repaired:runtime_scaffold/src/parser/parser.c:fallback",
                executions_by_type["create_scaffold_tree"]["output_text"],
            )
            content = (project_root / "runtime_scaffold" / "src" / "parser" / "parser.c").read_text(
                encoding="utf-8"
            )
            self.assertNotIn('#include "proto.h"', content)
            self.assertIn("generated_scaffold", content)

    def test_run_rejects_scaffold_manifest_paths_outside_runtime_scaffold(self) -> None:
        class EscapingManifestClient(FakeOllamaClient):
            def chat_with_options(
                self,
                *,
                model: str,
                messages,
                options=None,
            ) -> str:
                user_prompt = messages[-1].content
                if "Scaffold Tree Contract:" in user_prompt:
                    return (
                        '{'
                        '"dirs":["src","include"],'
                        '"files":[{"path":"src/main.c","purpose":"Bad escaped path."}]'
                        "}"
                    )
                return super().chat_with_options(
                    model=model,
                    messages=messages,
                    options=options,
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_root = root / "Projects" / "EscapingManifestProject"
            project_root.mkdir(parents=True)
            (root / "Projects" / "EscapingManifestProject.md").write_text(
                "# EscapingManifestProject\nUse this project to validate manifest path isolation.\n",
                encoding="utf-8",
            )

            _fake_client, service = self._build_service(
                root,
                fake_client=EscapingManifestClient(),
            )
            payload = self._run_payload(
                service,
                "Inspect Projects/EscapingManifestProject and create a scaffold tree for a C project.",
                model="gemma:latest",
                scope_dirs=("Projects",),
            )
            executions_by_type = self._executions_by_type(payload)

            self.assertEqual(executions_by_type["create_scaffold_tree"]["status"], "executed")
            self.assertTrue((project_root / "runtime_scaffold" / "src").is_dir())
            self.assertTrue((project_root / "runtime_scaffold" / "src" / "main.txt").is_file())
            self.assertFalse((project_root / "src").exists())
            self.assertFalse((project_root / "include").exists())

    def test_run_persists_agent_artifact_when_repository_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser and executor.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell").mkdir()

            history_repository = FakeAgentHistoryRepository()
            _fake_client, service = self._build_service(
                root,
                history_repository=history_repository,
            )

            service.run(
                "Build the mandatory part of minishell.",
                model="deepseek-r1:8b",
                scope_dirs=("Projects",),
            )

            self.assertEqual(len(history_repository.saved), 1)
            self.assertEqual(history_repository.saved[0]["model"], "deepseek-r1:8b")
            self.assertEqual(history_repository.saved[0]["status"], "needs_execution_layer")
            self.assertIsNotNone(history_repository.saved[0]["latency_ms"])

    def test_run_can_use_multi_model_discussion_for_planning(self) -> None:
        previous_values = {
            "PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION": os.environ.get("PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"),
            "PERSONAL_AI_AGENT_PLANNER_MODEL": os.environ.get("PERSONAL_AI_AGENT_PLANNER_MODEL"),
            "PERSONAL_AI_AGENT_CRITIC_MODEL": os.environ.get("PERSONAL_AI_AGENT_CRITIC_MODEL"),
            "PERSONAL_AI_AGENT_SYNTHESIS_MODEL": os.environ.get("PERSONAL_AI_AGENT_SYNTHESIS_MODEL"),
        }
        os.environ["PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"] = "true"
        os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = "gemma:latest"
        os.environ["PERSONAL_AI_AGENT_CRITIC_MODEL"] = "qwen2.5-coder:7b"
        os.environ["PERSONAL_AI_AGENT_SYNTHESIS_MODEL"] = "deepseek-r1:8b"
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "Projects").mkdir()
                (root / "Projects" / "Minishell.md").write_text(
                    "# Minishell\nImplement parser and executor.\n",
                    encoding="utf-8",
                )
                (root / "Projects" / "Minishell").mkdir()

                fake_client, service = self._build_service(root)
                payload = self._run_payload(
                    service,
                    "Build the mandatory part of minishell.",
                    model="gemma3:4b",
                    scope_dirs=("Projects",),
                    reasoning_mode="high",
                )

                self.assertEqual(payload["model"], "gemma:latest")
                self.assertEqual(payload["critic_model"], "qwen2.5-coder:7b")
                self.assertEqual(payload["synthesis_model"], "deepseek-r1:8b")
                self.assertEqual(payload["overview"]["planner_model"], "gemma:latest")
                self.assertEqual(payload["overview"]["critic_model"], "qwen2.5-coder:7b")
                self.assertEqual(payload["overview"]["synthesis_model"], "deepseek-r1:8b")
                self.assertGreaterEqual(len(fake_client.calls), 3)
                self.assertEqual(fake_client.calls[0][0], "gemma:latest")
                self.assertEqual(fake_client.calls[1][0], "qwen2.5-coder:7b")
                self.assertEqual(fake_client.calls[2][0], "deepseek-r1:8b")
                self.assertIn("Recursive Planning Critique:", fake_client.calls[1][1][-1].content)
                self.assertIn("Recursive Planning Final Pass:", fake_client.calls[2][1][-1].content)
        finally:
            for key, value in previous_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_run_falls_back_when_discussion_model_returns_empty_response(self) -> None:
        class FailingDiscussionClient(FakeOllamaClient):
            def chat_with_options(
                self,
                *,
                model: str,
                messages,
                options=None,
            ) -> str:
                if model == "deepseek-r1:8b" and "Recursive Planning Final Pass:" in messages[-1].content:
                    raise RuntimeError("Ollama returned an empty response.")
                return super().chat_with_options(
                    model=model,
                    messages=messages,
                    options=options,
                )

        previous_values = {
            "PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION": os.environ.get("PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"),
            "PERSONAL_AI_AGENT_PLANNER_MODEL": os.environ.get("PERSONAL_AI_AGENT_PLANNER_MODEL"),
            "PERSONAL_AI_AGENT_CRITIC_MODEL": os.environ.get("PERSONAL_AI_AGENT_CRITIC_MODEL"),
            "PERSONAL_AI_AGENT_SYNTHESIS_MODEL": os.environ.get("PERSONAL_AI_AGENT_SYNTHESIS_MODEL"),
        }
        os.environ["PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION"] = "true"
        os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = "gemma:latest"
        os.environ["PERSONAL_AI_AGENT_CRITIC_MODEL"] = "qwen2.5-coder:7b"
        os.environ["PERSONAL_AI_AGENT_SYNTHESIS_MODEL"] = "deepseek-r1:8b"
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / "Projects").mkdir()
                (root / "Projects" / "Minishell.md").write_text(
                    "# Minishell\nImplement parser and executor.\n",
                    encoding="utf-8",
                )
                (root / "Projects" / "Minishell").mkdir()

                _fake_client, service = self._build_service(
                    root,
                    fake_client=FailingDiscussionClient(),
                    recursive_refinement_enabled=True,
                )
                payload = self._run_payload(
                    service,
                    "Build the mandatory part of minishell.",
                    model="gemma3:4b",
                    scope_dirs=("Projects",),
                    reasoning_mode="high",
                )

                self.assertEqual(payload["status"], "needs_execution_layer")
                self.assertTrue(payload["steps"][1]["output_text"])
        finally:
            for key, value in previous_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

from __future__ import annotations

import unittest
from pathlib import Path

from personal_ai.application.agent_tool_registry import (
    AgentToolContext,
    AgentToolRegistry,
)
from personal_ai.domain.models import AgentRuntimeAction


class AgentToolRegistryTests(unittest.TestCase):
    def test_execute_returns_deferred_for_unknown_action(self) -> None:
        registry = AgentToolRegistry()
        action = AgentRuntimeAction(
            action_type="unknown_action",
            title="Unknown",
            target="none",
            instruction="Do something.",
            rationale="Test fallback.",
        )
        result = registry.execute(
            action,
            context=AgentToolContext(
                retrieval_notes={},
                resolved_repo_path=None,
                repo_summary=None,
                build_config_summary=None,
                model="gemma:latest",
                request_text="build minishell",
                normalized_goal="build minishell",
                planning_output="Goal\nConstraints",
                citations=(),
            ),
        )

        self.assertEqual(result.status, "deferred")
        self.assertEqual(result.action_type, "unknown_action")

    def test_execute_uses_registered_executor(self) -> None:
        registry = AgentToolRegistry()
        action = AgentRuntimeAction(
            action_type="inspect_note",
            title="Inspect Note",
            target="Projects/Note.md",
            instruction="Read the note.",
            rationale="Ground context.",
        )

        def executor(executed_action, context):
            return __import__(
                "personal_ai.domain.models",
                fromlist=["AgentRuntimeActionExecution"],
            ).AgentRuntimeActionExecution(
                action_type=executed_action.action_type,
                target=context.resolved_repo_path.as_posix() if context.resolved_repo_path else executed_action.target,
                status="executed",
                output_text="ok",
            )

        registry.register("inspect_note", executor)
        result = registry.execute(
            action,
            context=AgentToolContext(
                retrieval_notes={},
                resolved_repo_path=Path("Projects/Minishell"),
                repo_summary=None,
                build_config_summary=None,
                model="gemma:latest",
                request_text="build minishell",
                normalized_goal="build minishell",
                planning_output="Goal\nConstraints",
                citations=(),
            ),
        )

        self.assertEqual(result.status, "executed")
        self.assertEqual(result.output_text, "ok")
        self.assertEqual(result.target, "Projects/Minishell")


if __name__ == "__main__":
    unittest.main()

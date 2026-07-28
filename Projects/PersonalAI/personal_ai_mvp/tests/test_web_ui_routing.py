from __future__ import annotations

import unittest

from application.chat.query_mapping import normalize_knowledge_query
from application.chat.routing import RequestRoutingService
from domain.models import PromptMessage
from web_app.api_helpers import (
    normalize_reasoning_mode,
    parse_conversation_history,
    parse_scope_dirs,
)


class WebUIRoutingTests(unittest.TestCase):
    def test_request_routing_service_routes_english_codegen_prompt_to_implementation(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt=(
                "Generate a full BSQ implementation in C: explain the architecture, modules, "
                "execution flow, edge cases, and provide a code skeleton with key functions."
            )
        )

        self.assertEqual(decision.workflow, "implementation")
        self.assertEqual(decision.reasoning_mode, "high")

    def test_request_routing_service_routes_project_scale_prompt_to_agent(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt=(
                "You are working inside my local project folder. "
                "Create the folders, headers, source files, and Makefile, then compile and fix errors."
            )
        )

        self.assertEqual(decision.workflow, "agent")
        self.assertEqual(decision.confidence, "high")

    def test_request_routing_service_routes_note_prompt_to_draft(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="Write a note about C parser cleanup rules and ownership.",
        )

        self.assertEqual(decision.workflow, "draft")
        self.assertIsNotNone(decision.derived_title)

    def test_request_routing_service_routes_english_note_prompt_to_draft(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="Create a note about pipe handling rules in minishell.",
        )

        self.assertEqual(decision.workflow, "draft")
        self.assertIsNotNone(decision.derived_title)

    def test_request_routing_service_routes_english_analyze_prompt_to_analyze(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="Analyze directory Projects/PersonalAI and say what is missing from the graph.",
        )

        self.assertEqual(decision.workflow, "analyze")
        self.assertEqual(decision.derived_directory, "Projects/PersonalAI")

    def test_request_routing_service_does_not_treat_knowledge_nodes_as_note_draft(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="Analyze C knowledge nodes we already have and what else to add to the graph.",
        )

        self.assertNotEqual(decision.workflow, "draft")

    def test_parse_scope_dirs_supports_commas_newlines_and_dedupes(self) -> None:
        scopes = parse_scope_dirs("Languages, Projects\nLanguages\nNetworking")

        self.assertEqual(scopes, ("Languages", "Projects", "Networking"))

    def test_parse_conversation_history_keeps_valid_user_and_assistant_turns(self) -> None:
        history = parse_conversation_history(
            [
                {"role": "user", "content": "First constraint."},
                {"role": "assistant", "content": "Acknowledged."},
                {"role": "system", "content": "Skip me."},
                {"role": "user", "content": "  "},
            ]
        )

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[1].role, "assistant")

    def test_normalize_reasoning_mode_supports_auto_standard_and_high(self) -> None:
        self.assertEqual(normalize_reasoning_mode("auto"), "auto")
        self.assertEqual(normalize_reasoning_mode("high"), "high")
        self.assertEqual(normalize_reasoning_mode("other"), "standard")

    def test_normalize_knowledge_query_supports_english_knowledge_node_text(self) -> None:
        normalized = normalize_knowledge_query(
            "Analyze the C knowledge nodes we already have in the graph and what else to add."
        )

        self.assertIn("Terminology clarification:", normalized)

    def test_request_routing_service_stale_title_does_not_override_agent_prompt(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt=(
                "You are working inside my local project folder. "
                "Create the folders, headers, source files, and Makefile, then compile and fix errors."
            ),
            title="Old Draft Title",
        )

        self.assertEqual(decision.workflow, "agent")

    def test_request_routing_service_stale_title_does_not_override_analyze_prompt(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="Analyze directory Projects/PersonalAI and show what is missing from the graph.",
            title="Old Draft Title",
        )

        self.assertEqual(decision.workflow, "analyze")

    def test_request_routing_service_locks_follow_up_to_previous_substantive_user_task(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="you did not finish the task",
            conversation_history=(
                PromptMessage(role="user", content="Generate code for bsq in C."),
                PromptMessage(role="assistant", content="Started with the file layout."),
            ),
        )

        self.assertEqual(decision.workflow, "implementation")
        self.assertIn("follow-up", decision.reason)

    def test_request_routing_service_ignores_follow_up_only_history_when_finding_anchor(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="continue",
            conversation_history=(
                PromptMessage(role="user", content="Generate code for bsq in C."),
                PromptMessage(role="assistant", content="Partial answer."),
                PromptMessage(role="user", content="you stopped"),
            ),
        )

        self.assertEqual(decision.workflow, "implementation")

    def test_request_routing_service_locks_short_unfinished_follow_up_without_exact_phrase(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="finish everything",
            conversation_history=(
                PromptMessage(role="user", content="Generate code for bsq in C."),
                PromptMessage(
                    role="assistant",
                    content=(
                        "Architecture\n- Use dynamic programming.\n\n"
                        "Code Skeleton\n```c\nint solve_bsq("
                    ),
                ),
            ),
        )

        self.assertEqual(decision.workflow, "implementation")
        self.assertIn("follow-up", decision.reason)

    def test_request_routing_service_locks_ukrainian_follow_up_to_previous_implementation_task(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="ти не завершив, допиши",
            conversation_history=(
                PromptMessage(role="user", content="Generate code for bsq in C."),
                PromptMessage(
                    role="assistant",
                    content=(
                        "Architecture\n- Use dynamic programming.\n\n"
                        "Code Skeleton\n```c\nint solve_bsq("
                    ),
                ),
            ),
        )

        self.assertEqual(decision.workflow, "implementation")
        self.assertIn("follow-up", decision.reason)


if __name__ == "__main__":
    unittest.main()

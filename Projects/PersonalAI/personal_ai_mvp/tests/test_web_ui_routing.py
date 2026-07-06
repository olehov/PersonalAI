from __future__ import annotations

import unittest

from personal_ai.application.query_mapping import normalize_knowledge_query
from personal_ai.application.request_routing_service import RequestRoutingService
from personal_ai.web_ui import (
    normalize_reasoning_mode,
    parse_conversation_history,
    parse_scope_dirs,
)


class WebUIRoutingTests(unittest.TestCase):
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

    def test_request_routing_service_does_not_treat_knowledge_nodes_as_note_draft(self) -> None:
        decision = RequestRoutingService().route_request(
            prompt="проаналізуй ноди по C які в нас є і що ще додати в граф",
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

    def test_normalize_knowledge_query_supports_real_ukrainian_utf8_text(self) -> None:
        normalized = normalize_knowledge_query(
            "проаналізуй ноди по C які в нас є і що ще додати в граф"
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

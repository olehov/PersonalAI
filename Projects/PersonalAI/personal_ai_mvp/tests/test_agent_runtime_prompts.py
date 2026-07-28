from __future__ import annotations

import unittest

from application.agent_runtime.prompts import (
    sanitize_planning_artifact,
    sanitize_structured_artifact,
)


class AgentRuntimePromptSanitizerTests(unittest.TestCase):
    def test_sanitize_planning_artifact_strips_meta_preface(self) -> None:
        raw = (
            "We need to produce the final planning artifact now.\n\n"
            "Goal\nBuild the parser first.\n\n"
            "Constraints\nStay narrow.\n\n"
            "Existing Context\nRepo inspected.\n\n"
            "Modules\nsrc/parsing.c\n\n"
            "Incremental Slices\n1. parser\n\n"
            "First Slice\nEdit parsing only.\n\n"
            "First Actions\n1. edit file\n\n"
            "Validation\n1. make all\n\n"
            "Runtime Limits\nPlan only.\n"
        )

        cleaned = sanitize_planning_artifact(raw)

        self.assertTrue(cleaned.startswith("Goal"))
        self.assertNotIn("We need to produce", cleaned)

    def test_sanitize_structured_artifact_keeps_first_known_heading(self) -> None:
        raw = (
            "APPROVED\n\n"
            "The draft is ready.\n\n"
            "Scope\nFirst parser slice only.\n\n"
            "Files\n- src/parsing.c\n\n"
            "Edits\n- add tokenizer state\n\n"
            "Risks\n- keep it narrow\n\n"
            "Validation Order\n1. make all\n"
        )

        cleaned = sanitize_structured_artifact(
            raw,
            headings=("Scope", "Files", "Edits", "Risks", "Validation Order"),
        )

        self.assertTrue(cleaned.startswith("Scope"))
        self.assertNotIn("APPROVED", cleaned)
        self.assertNotIn("The draft is ready.", cleaned)


if __name__ == "__main__":
    unittest.main()

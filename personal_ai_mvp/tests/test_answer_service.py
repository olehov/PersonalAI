from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from application.knowledge.answer_service import AnswerService
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.shared.serializers import serialize_answer_bundle


class AnswerServiceTests(unittest.TestCase):
    def test_prepare_answer_builds_grounded_prompt_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI architecture overview.\n[[Vision]]\n",
                encoding="utf-8",
            )
            (root / "Vision.md").write_text(
                "# Vision\nPersonalAI long-term direction.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "how does personalai architecture work"
            )
            payload = serialize_answer_bundle(answer)

            self.assertEqual(payload["question"], "how does personalai architecture work")
            self.assertEqual(payload["task_mode"], "general")
            self.assertEqual(payload["messages"][0]["role"], "system")
            self.assertEqual(payload["messages"][1]["role"], "user")
            self.assertIn("Architecture.md", payload["citations"])
            self.assertIn("focused first on writing code", payload["messages"][0]["content"])
            self.assertIn("Reason carefully before answering", payload["messages"][0]["content"])
            self.assertIn("Treat the user as asking for software implementation help first.", payload["messages"][1]["content"])
            self.assertIn("When multiple designs are possible", payload["messages"][1]["content"])
            self.assertIn("Primary Notes:", payload["messages"][1]["content"])

    def test_answer_payload_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Vision.md").write_text("# Vision\nDirection.\n", encoding="utf-8")

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer("vision")
            payload = serialize_answer_bundle(answer)

            serialized = json.dumps(payload)
            self.assertIn("Vision.md", serialized)

    def test_answer_excerpt_focuses_on_relevant_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Dijkstra.md").write_text(
                "# Dijkstra\n"
                "Overview line.\n"
                "## Basics\n"
                "Unrelated intro.\n"
                "## Complexity\n"
                "Uses a priority queue and heap for shortest path processing.\n"
                "Time complexity is O((V + E) log V).\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "dijkstra priority queue complexity"
            )
            payload = serialize_answer_bundle(answer)
            prompt = payload["messages"][1]["content"]

            self.assertIn("## Complexity", prompt)
            self.assertIn("priority queue and heap", prompt)
            self.assertNotIn("Overview line.", prompt)

    def test_answer_payload_prunes_weak_related_tail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Design Patterns").mkdir()
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nPriority queue operations and heap implementation.\n[[Heap]]\n[[Heapsort]]\n[[Queues and Backpressure]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Dijkstra.md").write_text(
                "# Dijkstra\nShortest path using a priority queue and heap.\n[[Heap]]\n[[Graph Traversal]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap operations and complexity.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Heapsort.md").write_text(
                "# Heapsort\nHeap-based sorting complexity.\n[[Heap]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Graph Traversal.md").write_text(
                "# Graph Traversal\nGraph shortest path traversal basics.\n[[Dijkstra]]\n",
                encoding="utf-8",
            )
            (root / "Design Patterns" / "Queues and Backpressure.md").write_text(
                "# Queues and Backpressure\nOperational queue flow control.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "how does dijkstra use a priority queue and what is the complexity",
                scope_dirs=("Algorithms",),
            )
            payload = serialize_answer_bundle(answer)
            prompt = payload["messages"][1]["content"]
            related_paths = [item["note"]["path"] for item in payload["retrieval"]["related_notes"]]
            related_section = prompt.split("Related Notes:\n", maxsplit=1)[1]

            self.assertLessEqual(len(related_paths), 3)
            self.assertIn("Algorithms/Heapsort.md", related_paths)
            self.assertNotIn("Design Patterns/Queues and Backpressure.md", related_paths)
            self.assertNotIn("Queues and Backpressure", related_section)

    def test_answer_payload_prunes_duplicate_primary_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\n## Basics\nPriority queue operations.\n## Complexity\nInsert and extract are O(log n).\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Dijkstra.md").write_text(
                "# Dijkstra\n## Complexity\nUses a priority queue backed by a heap.\nTime complexity is O((V + E) log V).\n[[Graph Traversal]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Graph Traversal.md").write_text(
                "# Graph Traversal\n## Complexity\nTime complexity is O(V + E).\nTraversal is used by graph algorithms including Dijkstra.\n[[Dijkstra]]\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "how does dijkstra use a priority queue and what is the complexity",
                scope_dirs=("Algorithms",),
            )
            payload = serialize_answer_bundle(answer)
            primary_paths = [item["note"]["path"] for item in payload["retrieval"]["primary_notes"]]
            prompt = payload["messages"][1]["content"]

            self.assertLessEqual(len(primary_paths), 2)
            self.assertIn("Algorithms/Priority Queue.md", primary_paths)
            self.assertIn("Algorithms/Dijkstra.md", primary_paths)
            self.assertNotIn("Algorithms/Graph Traversal.md", primary_paths)
            self.assertNotIn("title: Graph Traversal", prompt)

    def test_answer_payload_switches_to_implementation_mode_for_build_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages").mkdir()
            (root / "Languages" / "C.md").write_text(
                "# C\nUse clear modules and parse input carefully.\n",
                encoding="utf-8",
            )
            (root / "Projects").mkdir()
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nImplement parser, executor, and builtins.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "implement a minishell parser and executor in C"
            )
            payload = serialize_answer_bundle(answer)
            prompt = payload["messages"][1]["content"]

            self.assertEqual(payload["task_mode"], "implementation")
            self.assertIn("Task Mode:\nimplementation", prompt)
            self.assertIn("implementation mode: lead with a concrete build plan or code skeleton", prompt)
            self.assertIn("Preferred Coverage:", prompt)
            self.assertIn("exact heading names are optional", prompt)
            self.assertIn("If you start a code block for a file, finish that file before ending the answer.", prompt)
            self.assertIn("Do not stop mid-function, mid-list, mid-file, or mid-sentence.", prompt)
            self.assertIn("Make a concrete decision when multiple implementation paths exist", prompt)
            self.assertIn("Do not start with generic theory or motivational text.", prompt)
            self.assertIn("do not force the whole answer into a rigid markdown document shape", prompt.casefold())
            self.assertIn("do not stop at architecture alone", prompt.casefold())
            self.assertIn("include at least one concrete code block or explicit file-by-file skeleton", prompt.casefold())

    def test_prepare_answer_uses_coding_mode_for_code_facing_non_build_question(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages").mkdir()
            (root / "Projects" / "Project Index.md").write_text(
                "# Project Index\nRoadmap and planning hub.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nParser and executor structure for the shell.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C Best Practices.md").write_text(
                "# C Best Practices\nKeep parser, executor, and cleanup logic separate.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Explain how to design a minimal command parser for minishell in C.",
                scope_dirs=("Projects", "Languages"),
            )
            payload = serialize_answer_bundle(answer)
            combined_paths = [
                item["note"]["path"]
                for item in (
                    list(payload["retrieval"]["primary_notes"]) + list(payload["retrieval"]["related_notes"])
                )
            ]

            self.assertEqual(payload["task_mode"], "coding")
            self.assertIn("Projects/Minishell.md", combined_paths)
            self.assertIn("Languages/C Best Practices.md", combined_paths)
            self.assertNotIn("Projects/Project Index.md", combined_paths)
            self.assertIn("This request is in coding mode", payload["messages"][1]["content"])

    def test_prepare_answer_supports_note_draft_mode_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages").mkdir()
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nProject planning and milestones.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "TCP and UDP.md").write_text(
                "# TCP and UDP\nTransport-layer protocol behavior and tradeoffs.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Prepare knowledge for note 'TCP Retransmission Basics'. Instruction: write the missing networking note.",
                scope_dirs=("Projects", "Languages"),
                retrieval_task_mode_override="note_draft",
            )
            payload = serialize_answer_bundle(answer)
            combined_paths = [
                item["note"]["path"]
                for item in (
                    list(payload["retrieval"]["primary_notes"]) + list(payload["retrieval"]["related_notes"])
                )
            ]

            self.assertEqual(payload["task_mode"], "general")
            self.assertIn("Languages/TCP and UDP.md", combined_paths)
            self.assertNotIn("Projects/Roadmap.md", combined_paths)
            self.assertNotIn("Projects/Roadmap.md", combined_paths)

    def test_prepare_answer_supports_agent_mode_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages").mkdir()
            (root / "Projects" / "Project Index.md").write_text(
                "# Project Index\nGeneral planning hub.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nParser slice should touch lexer, parser, and command structures.\n[[Header Design in C]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "Header Design in C.md").write_text(
                "# Header Design in C\nKeep minishell parser interfaces explicit and minimal for the first parser slice.\n[[Minishell]]\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Inspect the minishell repository and plan the first parser slice.",
                scope_dirs=("Projects", "Languages"),
                retrieval_task_mode_override="agent",
            )
            payload = serialize_answer_bundle(answer)
            combined_paths = [
                item["note"]["path"]
                for item in (
                    list(payload["retrieval"]["primary_notes"]) + list(payload["retrieval"]["related_notes"])
                )
            ]

            self.assertEqual(payload["task_mode"], "coding")
            self.assertIn("Projects/Minishell.md", combined_paths)
            self.assertIn("Languages/Header Design in C.md", combined_paths)
            self.assertNotIn("Projects/Project Index.md", combined_paths)

    def test_prepare_answer_supports_high_reasoning_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPrefer explicit module boundaries and careful cleanup.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "compare two parser designs and pick the safer one",
                reasoning_mode="high",
            )
            payload = serialize_answer_bundle(answer)

            self.assertIn("deeper reasoning pass", payload["messages"][0]["content"])
            self.assertIn("Reasoning Mode:\nhigh", payload["messages"][1]["content"])
            self.assertIn("High Reasoning Mode:", payload["messages"][1]["content"])

    def test_prepare_answer_maps_knowledge_nodes_to_obsidian_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages").mkdir()
            (root / "Languages" / "C Best Practices.md").write_text(
                "# C Best Practices\nUse clear modules and check allocation failures.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Analyze the C knowledge nodes we already have and what else to add to the graph.",
                scope_dirs=("Languages",),
            )
            payload = serialize_answer_bundle(answer)

            self.assertEqual(
                payload["question"],
                "Analyze the C knowledge nodes we already have and what else to add to the graph.",
            )
            self.assertIn(
                "Terminology clarification: in this request, nodes means knowledge-base notes",
                payload["messages"][1]["content"],
            )

    def test_implementation_retrieval_prefers_reference_notes_over_project_meta_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages").mkdir()
            (root / "Projects" / "Project Index.md").write_text(
                "# PersonalAI Project Index\nOverview of the project graph.\n[[Roadmap]]\n[[BSQ Project]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nFuture milestones for the PersonalAI project.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "BSQ Project.md").write_text(
                "# BSQ Project\nParse the map, compute the largest square, and print the marked result.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C Best Practices.md").write_text(
                "# C Best Practices\nUse small modules, check allocation failures, and keep parsing separate from DP logic.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "Memory Management in C.md").write_text(
                "# Memory Management in C\nFree partially allocated rows on failure and centralize cleanup paths.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Generate a full BSQ implementation in C with modules, execution flow, and edge cases.",
                scope_dirs=("Projects", "Languages"),
            )
            payload = serialize_answer_bundle(answer)
            primary_paths = [item["note"]["path"] for item in payload["retrieval"]["primary_notes"]]
            related_paths = [item["note"]["path"] for item in payload["retrieval"]["related_notes"]]
            combined_paths = primary_paths + related_paths

            self.assertEqual(payload["task_mode"], "implementation")
            self.assertIn("Projects/BSQ Project.md", combined_paths)
            self.assertIn("Languages/C Best Practices.md", combined_paths)
            self.assertNotIn("Projects/Project Index.md", combined_paths)
            self.assertNotIn("Projects/Roadmap.md", combined_paths)

    def test_general_retrieval_can_still_return_project_meta_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Project Index.md").write_text(
                "# PersonalAI Project Index\nOverview of the project graph and linked planning notes.\n[[Roadmap]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nThe roadmap tracks milestones, priorities, and delivery direction.\n[[Project Index]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Vision.md").write_text(
                "# Vision\nHigh-level product direction.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "What does the PersonalAI roadmap say about project direction?",
                scope_dirs=("Projects",),
            )
            payload = serialize_answer_bundle(answer)
            combined_paths = [
                item["note"]["path"]
                for item in (
                    list(payload["retrieval"]["primary_notes"]) + list(payload["retrieval"]["related_notes"])
                )
            ]

            self.assertEqual(payload["task_mode"], "general")
            self.assertIn("Projects/Roadmap.md", combined_paths)
            self.assertIn("Projects/Project Index.md", combined_paths)

    def test_implementation_retrieval_ignores_personalai_project_notes_for_unrelated_bsq_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects").mkdir(exist_ok=True)
            (root / "Languages").mkdir()
            (root / "Projects" / "PersonalAI" / "Architecture.md").write_text(
                "# PersonalAI Architecture\nPlanner, agent runtime, and roadmap notes.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nDelivery milestones for the assistant.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "BSQ Project.md").write_text(
                "# BSQ Project\nParse the grid, compute the largest square, and print the marked map.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C Best Practices.md").write_text(
                "# C Best Practices\nKeep parsing, DP, and cleanup separated into small modules.\n",
                encoding="utf-8",
            )

            knowledge = KnowledgeService(root)
            knowledge.load()
            answer = AnswerService(RetrievalService(knowledge)).prepare_answer(
                "Generate a full BSQ implementation in C with modules, execution flow, and edge cases.",
                scope_dirs=("Projects", "Languages"),
            )
            payload = serialize_answer_bundle(answer)
            combined_paths = [
                item["note"]["path"]
                for item in (
                    list(payload["retrieval"]["primary_notes"]) + list(payload["retrieval"]["related_notes"])
                )
            ]

            self.assertIn("Projects/BSQ Project.md", combined_paths)
            self.assertIn("Languages/C Best Practices.md", combined_paths)
            self.assertNotIn("Projects/PersonalAI/Architecture.md", combined_paths)
            self.assertNotIn("Projects/PersonalAI/Roadmap.md", combined_paths)


if __name__ == "__main__":
    unittest.main()

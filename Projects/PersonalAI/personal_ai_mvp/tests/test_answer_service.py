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


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.knowledge.directory_analysis_service import (
    DirectoryAnalysisService,
)
from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.shared.serializers import (
    serialize_directory_analysis_report,
    serialize_note,
    serialize_retrieval_bundle,
)


class CountingEmbeddingProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_text(self, text: str) -> tuple[float, ...]:
        self.calls.append(text)
        return (float(len(text)), 1.0)


class KnowledgeServiceTests(unittest.TestCase):
    def test_loads_vault_and_exposes_queries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text("# Architecture\n[[Vision]]\n", encoding="utf-8")
            (root / "Vision.md").write_text("---\nkind: note\n---\n# Vision\nDirection.\n", encoding="utf-8")

            service = KnowledgeService(root)
            service.load()

            self.assertEqual(service.scan_summary()["note_count"], 2)
            self.assertEqual(service.search_notes("direction")[0].title, "Vision")
            self.assertEqual(service.get_related_notes("Architecture")[0].title, "Vision")

    def test_serialize_note_returns_json_friendly_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Vision.md").write_text("# Vision\n", encoding="utf-8")

            service = KnowledgeService(root)
            service.load()
            note = service.get_note("Vision")

            self.assertIsNotNone(note)
            payload = serialize_note(note)
            self.assertEqual(payload["path"], "Vision.md")
            self.assertEqual(payload["title"], "Vision")

    def test_retrieval_service_builds_context_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture.md").write_text(
                "# Architecture\nPersonalAI retrieval design.\n[[Vision]]\n",
                encoding="utf-8",
            )
            (root / "Vision.md").write_text(
                "# Vision\nPersonalAI long-term architecture direction.\n",
                encoding="utf-8",
            )
            (root / "Linux.md").write_text("# Linux\nKernel notes.\n", encoding="utf-8")

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context("personalai architecture")
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(payload["question"], "personalai architecture")
            self.assertEqual(payload["primary_notes"][0]["note"]["title"], "Architecture")
            self.assertIn("debug_signals", payload["primary_notes"][0])
            self.assertIn("note_class", payload["primary_notes"][0]["debug_signals"])
            selected_titles = {
                item["note"]["title"] for item in payload["primary_notes"] + payload["related_notes"]
            }
            self.assertIn("Vision", selected_titles)

    def test_retrieval_prefers_technical_directory_over_meta_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Projects").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap insert extract complexity operations.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "README.md").write_text(
                "# Project README\nHeap project overview and roadmap.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context("heap operations complexity")
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(payload["primary_notes"][0]["note"]["title"], "Heap")
            self.assertEqual(payload["primary_notes"][0]["note"]["path"], "Algorithms/Heap.md")

    def test_retrieval_uses_semantic_vector_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Architecture Decisions").mkdir()
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nHeap-based scheduling with enqueue and dequeue operations.\n",
                encoding="utf-8",
            )
            (root / "Architecture Decisions" / "Roadmap.md").write_text(
                "# Roadmap\nProject planning and milestones.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context("heap scheduling queue operations")
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(payload["primary_notes"][0]["note"]["path"], "Algorithms/Priority Queue.md")
            self.assertIn("semantic match", payload["primary_notes"][0]["reason"])
            self.assertGreater(
                payload["primary_notes"][0]["debug_signals"]["semantic"]["points"],
                0,
            )

    def test_retrieval_scope_limits_results_to_requested_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Projects").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nInsert extract complexity.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Heap.md").write_text(
                "# Heap Project\nRoadmap and planning.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "heap complexity",
                scope_dirs=("Algorithms",),
            )
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(len(payload["primary_notes"]), 1)
            self.assertEqual(payload["primary_notes"][0]["note"]["path"], "Algorithms/Heap.md")

    def test_retrieval_scope_supports_nested_directory_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Languages" / "Python").mkdir(parents=True)
            (root / "Languages" / "C" / "Parsing and Validation in C.md").write_text(
                "# Parsing and Validation in C\nValidate rows, dimensions, and symbols.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "Python" / "Lists.md").write_text(
                "# Lists\nPython list operations.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "parsing validation in c",
                scope_dirs=("Languages/C",),
            )
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(len(payload["primary_notes"]), 1)
            self.assertEqual(
                payload["primary_notes"][0]["note"]["path"],
                "Languages/C/Parsing and Validation in C.md",
            )

    def test_cross_domain_query_promotes_bridge_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Bugs").mkdir()
            (root / "Design Patterns").mkdir()
            (root / "Networking").mkdir()
            (root / "Linux").mkdir()
            (root / "Bugs" / "Retries and Timeouts.md").write_text(
                "# Retries and Timeouts\nRetries with backoff and timeout control.\n",
                encoding="utf-8",
            )
            (root / "Design Patterns" / "Queues and Backpressure.md").write_text(
                "# Queues and Backpressure\nBackpressure protects overloaded consumers.\n",
                encoding="utf-8",
            )
            (root / "Networking" / "HTTP.md").write_text(
                "# HTTP\nRequest and response transport.\n",
                encoding="utf-8",
            )
            (root / "Linux" / "SSH.md").write_text(
                "# SSH\nRemote shell debugging.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "how do retries, timeouts, and backpressure interact in distributed systems"
            )
            payload = serialize_retrieval_bundle(bundle)

            primary_paths = [item["note"]["path"] for item in payload["primary_notes"]]
            self.assertIn("Bugs/Retries and Timeouts.md", primary_paths)
            self.assertIn("Design Patterns/Queues and Backpressure.md", primary_paths)

    def test_observability_query_promotes_observability_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Architecture Decisions").mkdir()
            (root / "Bugs").mkdir()
            (root / "Linux").mkdir()
            (root / "Networking").mkdir()
            (root / "Architecture Decisions" / "Observability.md").write_text(
                "# Observability\nLogs, metrics, and traces for debugging systems.\n",
                encoding="utf-8",
            )
            (root / "Bugs" / "Retries and Timeouts.md").write_text(
                "# Retries and Timeouts\nTimeouts around HTTP requests and service restarts.\n",
                encoding="utf-8",
            )
            (root / "Linux" / "Systemd.md").write_text(
                "# Systemd\nService manager with logs.\n",
                encoding="utf-8",
            )
            (root / "Networking" / "HTTP.md").write_text(
                "# HTTP\nApplication protocol for request and response flows.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "how does observability help with systemd and http debugging"
            )
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(
                payload["primary_notes"][0]["note"]["path"],
                "Architecture Decisions/Observability.md",
            )
            self.assertIn("bridge note bonus", payload["primary_notes"][0]["reason"])
            self.assertIn("focus match", payload["primary_notes"][0]["reason"])

    def test_graph_reranking_promotes_central_note(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nPriority queue heap operations.\n[[Priority Queue]]\n[[Dijkstra]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nQueue operations and scheduling.\n[[Heap]]\n[[Dijkstra]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Dijkstra.md").write_text(
                "# Dijkstra\nShortest path graph algorithm using a priority queue and heap.\n[[Heap]]\n[[Priority Queue]]\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context("priority queue graph shortest path")
            payload = serialize_retrieval_bundle(bundle)

            primary_paths = [item["note"]["path"] for item in payload["primary_notes"]]
            self.assertIn("Algorithms/Dijkstra.md", primary_paths)
            self.assertTrue(
                any("graph link bonus" in item["reason"] for item in payload["primary_notes"])
            )

    def test_related_notes_accumulate_score_from_multiple_primary_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Networking").mkdir()
            (root / "Architecture Decisions").mkdir()
            (root / "Networking" / "HTTP.md").write_text(
                "# HTTP\nApplication protocol.\n[[Observability]]\n",
                encoding="utf-8",
            )
            (root / "Networking" / "Load Balancing.md").write_text(
                "# Load Balancing\nTraffic distribution.\n[[Observability]]\n",
                encoding="utf-8",
            )
            (root / "Architecture Decisions" / "Observability.md").write_text(
                "# Observability\nLogs metrics traces.\n[[HTTP]]\n[[Load Balancing]]\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "http load balancing",
                primary_limit=2,
                related_limit=3,
            )
            payload = serialize_retrieval_bundle(bundle)

            related_paths = [item["note"]["path"] for item in payload["related_notes"]]
            self.assertIn("Architecture Decisions/Observability.md", related_paths)
            observability = next(
                item for item in payload["related_notes"]
                if item["note"]["path"] == "Architecture Decisions/Observability.md"
            )
            self.assertIn("linked from HTTP", observability["reason"])
            self.assertIn("linked from Load Balancing", observability["reason"])
            self.assertEqual(
                set(observability["debug_signals"]["linked_from"]),
                {"HTTP", "Load Balancing"},
            )

    def test_primary_selection_prefers_complementary_notes_over_near_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nPriority queue operations, heap implementation, and complexity.\n[[Dijkstra]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Priority Queue Operations.md").write_text(
                "# Priority Queue Operations\nPriority queue operations, heap implementation, and complexity details.\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Dijkstra.md").write_text(
                "# Dijkstra\nShortest path algorithm using a priority queue and heap with graph complexity.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "priority queue shortest path complexity",
                primary_limit=2,
            )
            payload = serialize_retrieval_bundle(bundle)

            primary_paths = [item["note"]["path"] for item in payload["primary_notes"]]
            self.assertIn("Algorithms/Priority Queue.md", primary_paths)
            self.assertIn("Algorithms/Dijkstra.md", primary_paths)
            self.assertNotIn("Algorithms/Priority Queue Operations.md", primary_paths)

    def test_related_notes_prune_unrelated_bridge_notes_for_narrow_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Optimizations").mkdir()
            (root / "Design Patterns").mkdir()
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nPriority queue operations and heap implementation.\n[[Heap]]\n[[Caching]]\n[[Queues and Backpressure]]\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap operations and complexity.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )
            (root / "Optimizations" / "Caching.md").write_text(
                "# Caching\nLatency and cache invalidation.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )
            (root / "Design Patterns" / "Queues and Backpressure.md").write_text(
                "# Queues and Backpressure\nBounded queues and flow control.\n[[Priority Queue]]\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "priority queue heap complexity",
                primary_limit=1,
                related_limit=5,
                scope_dirs=("Algorithms",),
            )
            payload = serialize_retrieval_bundle(bundle)

            related_paths = [item["note"]["path"] for item in payload["related_notes"]]
            self.assertIn("Algorithms/Heap.md", related_paths)
            self.assertNotIn("Optimizations/Caching.md", related_paths)
            self.assertNotIn("Design Patterns/Queues and Backpressure.md", related_paths)

    def test_focused_coding_query_prefers_minishell_note_over_project_meta_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Projects" / "Project Index.md").write_text(
                "# Project Index\nMinishell project overview, roadmap, and links.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "README.md").write_text(
                "# README\nBuild the minishell project and review the roadmap.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Minishell.md").write_text(
                "# Minishell\nParser, executor, redirections, pipes, and builtin dispatch in C.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Memory Management in C.md").write_text(
                "# Memory Management in C\nAllocation, cleanup, and ownership rules.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "generate code for minishell parser and executor in C",
                scope_dirs=("Projects", "Languages"),
            )
            payload = serialize_retrieval_bundle(bundle)

            primary_paths = [item["note"]["path"] for item in payload["primary_notes"]]
            self.assertEqual(primary_paths[0], "Projects/Minishell.md")
            self.assertNotEqual(primary_paths[0], "Projects/Project Index.md")
            self.assertNotEqual(primary_paths[0], "Projects/README.md")

    def test_focused_coding_related_notes_do_not_pull_project_meta_tail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Projects" / "BSQ.md").write_text(
                "# BSQ\nLargest square dynamic-programming solution in C.\n[[Memory Management in C]]\n[[Project Index]]\n",
                encoding="utf-8",
            )
            (root / "Projects" / "Project Index.md").write_text(
                "# Project Index\nBSQ overview, roadmap, and team notes.\n[[BSQ]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Memory Management in C.md").write_text(
                "# Memory Management in C\nAllocation, cleanup, and bounds-checking rules.\n[[BSQ]]\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "write a single-file C program for bsq",
                scope_dirs=("Projects", "Languages"),
                primary_limit=1,
                related_limit=4,
            )
            payload = serialize_retrieval_bundle(bundle)

            related_paths = [item["note"]["path"] for item in payload["related_notes"]]
            self.assertIn("Languages/C/Memory Management in C.md", related_paths)
            self.assertNotIn("Projects/Project Index.md", related_paths)

    def test_implementation_note_class_weighting_prefers_reference_notes_over_meta_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Projects" / "README.md").write_text(
                "# README\nC project overview, delivery notes, and milestones.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "BSQ.md").write_text(
                "# BSQ\nBuild BSQ in C with parser, solver, and output renderer.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Parsing and Validation in C.md").write_text(
                "# Parsing and Validation in C\nTokenize input, validate dimensions, and keep parsing errors explicit.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "implement bsq parser and validation in C",
                scope_dirs=("Projects", "Languages"),
                task_mode="implementation",
            )
            payload = serialize_retrieval_bundle(bundle)

            primary_paths = [item["note"]["path"] for item in payload["primary_notes"]]
            primary_reasons = [item["reason"] for item in payload["primary_notes"]]
            self.assertEqual(primary_paths[0], "Languages/C/Parsing and Validation in C.md")
            self.assertIn("Projects/BSQ.md", primary_paths)
            self.assertNotIn("Projects/README.md", primary_paths)
            self.assertTrue(any("note class: reference" in reason for reason in primary_reasons))

    def test_project_queries_can_prefer_project_meta_notes_in_general_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects").mkdir()
            (root / "Projects" / "Roadmap.md").write_text(
                "# Roadmap\nDelivery priorities, milestones, and next phases.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "BSQ.md").write_text(
                "# BSQ\nImplementation details for the BSQ project.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "what does the project roadmap say about next phases",
                scope_dirs=("Projects",),
                task_mode="general",
            )
            payload = serialize_retrieval_bundle(bundle)

            self.assertEqual(payload["primary_notes"][0]["note"]["path"], "Projects/Roadmap.md")
            self.assertIn("note class: project_meta", payload["primary_notes"][0]["reason"])
            self.assertEqual(
                payload["primary_notes"][0]["debug_signals"]["note_class"],
                "project_meta",
            )

    def test_unrelated_implementation_query_penalizes_personalai_project_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Projects" / "PersonalAI").mkdir(parents=True)
            (root / "Projects" / "PersonalAI" / "Architecture.md").write_text(
                "# PersonalAI Architecture\nPlanner loops, roadmap notes, and agent runtime internals.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "PersonalAI" / "Roadmap.md").write_text(
                "# PersonalAI Roadmap\nAssistant delivery milestones.\n",
                encoding="utf-8",
            )
            (root / "Projects" / "BSQ.md").write_text(
                "# BSQ\nBuild BSQ in C with parser, solver, and output rendering.\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Languages" / "C" / "Parsing and Validation in C.md").write_text(
                "# Parsing and Validation in C\nValidate dimensions, rows, and obstacle characters.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            bundle = RetrievalService(service).build_context(
                "generate a full BSQ implementation in C with modules and edge cases",
                scope_dirs=("Projects", "Languages"),
                task_mode="implementation",
            )
            payload = serialize_retrieval_bundle(bundle)

            combined = payload["primary_notes"] + payload["related_notes"]
            combined_paths = [item["note"]["path"] for item in combined]
            penalties = {
                item["note"]["path"]: item["debug_signals"]["penalties"].get("self_project", 0)
                for item in payload["primary_notes"]
            }

            self.assertIn("Projects/BSQ.md", combined_paths)
            self.assertIn("Languages/C/Parsing and Validation in C.md", combined_paths)
            self.assertNotIn("Projects/PersonalAI/Architecture.md", combined_paths)
            self.assertNotIn("Projects/PersonalAI/Roadmap.md", combined_paths)
            self.assertGreaterEqual(
                penalties.get("Projects/BSQ.md", 0),
                0,
            )

    def test_directory_analysis_reports_directory_inventory_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Languages" / "C").mkdir(parents=True)
            (root / "Languages" / "C" / "File IO in C.md").write_text(
                "# File I/O in C\nReading and writing files.\n[[Error Handling in C]]\n[[stdio]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Error Handling in C.md").write_text(
                "# Error Handling in C\nUse errno and perror.\n[[File IO in C]]\n",
                encoding="utf-8",
            )
            (root / "Languages" / "C" / "Header Design in C.md").write_text(
                "# Header Design in C\nDesign clear .h files.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            report = DirectoryAnalysisService(service).analyze_directory("Languages/C")
            payload = serialize_directory_analysis_report(report)

            self.assertEqual(payload["directory"], "Languages/C")
            self.assertEqual(payload["note_count"], 3)
            self.assertEqual(payload["internal_link_count"], 2)
            self.assertIn("stdio", payload["unresolved_links"])
            self.assertIn("Languages/C/Header Design in C.md", payload["isolated_notes"])
            suggestion_titles = {item["title"] for item in payload["suggestions"]}
            self.assertIn("Build and Tooling for C", suggestion_titles)
            self.assertIn("Strings and Character Arrays in C", suggestion_titles)

    def test_retrieval_reuses_vector_index_when_knowledge_revision_and_scope_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap insert extract complexity operations.\n",
                encoding="utf-8",
            )
            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nHeap-based scheduling with enqueue and dequeue operations.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            embedding_provider = CountingEmbeddingProvider()
            retrieval = RetrievalService(service, embedding_provider=embedding_provider)

            retrieval.build_context("heap operations", scope_dirs=("Algorithms",))
            first_call_count = len(embedding_provider.calls)
            retrieval.build_context("priority queue", scope_dirs=("Algorithms",))
            second_call_count = len(embedding_provider.calls)

            self.assertEqual(first_call_count, 3)
            self.assertEqual(second_call_count, 4)

    def test_retrieval_rebuilds_vector_index_after_knowledge_reload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Algorithms").mkdir()
            (root / "Algorithms" / "Heap.md").write_text(
                "# Heap\nHeap insert extract complexity operations.\n",
                encoding="utf-8",
            )

            service = KnowledgeService(root)
            service.load()
            embedding_provider = CountingEmbeddingProvider()
            retrieval = RetrievalService(service, embedding_provider=embedding_provider)

            retrieval.build_context("heap operations", scope_dirs=("Algorithms",))
            first_call_count = len(embedding_provider.calls)

            (root / "Algorithms" / "Priority Queue.md").write_text(
                "# Priority Queue\nHeap-based scheduling with enqueue and dequeue operations.\n",
                encoding="utf-8",
            )
            service.load()
            retrieval.build_context("priority queue", scope_dirs=("Algorithms",))
            second_call_count = len(embedding_provider.calls)

            self.assertEqual(first_call_count, 2)
            self.assertEqual(second_call_count, 5)


if __name__ == "__main__":
    unittest.main()

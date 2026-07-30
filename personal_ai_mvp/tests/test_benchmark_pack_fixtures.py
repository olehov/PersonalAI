from __future__ import annotations

import unittest
from pathlib import Path

from application.benchmark.pack_service import BenchmarkPackService


class BenchmarkPackFixtureTests(unittest.TestCase):
    def test_retrieval_drift_pack_loads_expected_tasks(self) -> None:
        pack_path = (
            Path(__file__).resolve().parent.parent
            / "training_examples"
            / "benchmarks"
            / "retrieval_drift_pack.json"
        )

        pack = BenchmarkPackService().load_pack(pack_path)

        self.assertEqual(pack.pack_id, "retrieval-drift-v1")
        self.assertEqual(len(pack.tasks), 3)
        self.assertEqual(
            tuple(task.task_id for task in pack.tasks),
            (
                "bsq-full-implementation-stays-on-bsq",
                "minishell-parser-query-prefers-shell-context",
                "c-gap-analysis-adds-missing-c-note",
            ),
        )
        self.assertTrue(all(task.category == "retrieval_regression" for task in pack.tasks))
        self.assertEqual(pack.tasks[0].workflow, "implementation")
        self.assertEqual(pack.tasks[1].workflow, "ask")
        self.assertTrue(
            any("library management system" in signal for signal in pack.tasks[0].anti_signals)
        )


if __name__ == "__main__":
    unittest.main()

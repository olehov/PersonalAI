from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.agent_runtime.action_support import resolve_safe_repo_write_path


class AgentRuntimeActionSupportTests(unittest.TestCase):
    def test_safe_repo_writes_allow_configured_hidden_runtime_scaffold_subtrees(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            scaffold_path, scaffold_error = resolve_safe_repo_write_path(
                resolved_repo_path=repo_root,
                target=".runtime/runtime_scaffold/src/main.c",
            )
            probe_path, probe_error = resolve_safe_repo_write_path(
                resolved_repo_path=repo_root,
                target=".runtime/runtime_write_probe/WRITE_PROBE.md",
            )
            other_runtime_path, other_runtime_error = resolve_safe_repo_write_path(
                resolved_repo_path=repo_root,
                target=".runtime/other/file.txt",
            )

            self.assertEqual(scaffold_error, None)
            self.assertEqual(
                scaffold_path,
                (repo_root / ".runtime" / "runtime_scaffold" / "src" / "main.c").resolve(),
            )
            self.assertEqual(probe_error, None)
            self.assertEqual(
                probe_path,
                (repo_root / ".runtime" / "runtime_write_probe" / "WRITE_PROBE.md").resolve(),
            )
            self.assertIsNone(other_runtime_path)
            self.assertEqual(
                other_runtime_error,
                "Safe repo writes cannot target restricted runtime or environment directories.",
            )


if __name__ == "__main__":
    unittest.main()

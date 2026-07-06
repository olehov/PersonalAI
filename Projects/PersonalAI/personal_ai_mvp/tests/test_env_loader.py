from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from personal_ai.infrastructure.env_loader import load_env_file, read_bool_env


class EnvLoaderTests(unittest.TestCase):
    def test_load_env_file_sets_values_and_strips_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "# comment\n"
                "OLLAMA_BASE_URL=http://127.0.0.1:11434\n"
                "PERSONAL_AI_DEFAULT_MODEL=\"gemma:latest\"\n"
                "export OLLAMA_TIMEOUT_SECONDS='420'\n",
                encoding="utf-8",
            )

            previous = {
                key: os.environ.get(key)
                for key in (
                    "OLLAMA_BASE_URL",
                    "PERSONAL_AI_DEFAULT_MODEL",
                    "OLLAMA_TIMEOUT_SECONDS",
                )
            }
            try:
                for key in previous:
                    os.environ.pop(key, None)
                loaded = load_env_file(env_path)

                self.assertEqual(loaded, env_path)
                self.assertEqual(os.environ["OLLAMA_BASE_URL"], "http://127.0.0.1:11434")
                self.assertEqual(os.environ["PERSONAL_AI_DEFAULT_MODEL"], "gemma:latest")
                self.assertEqual(os.environ["OLLAMA_TIMEOUT_SECONDS"], "420")
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_load_env_file_respects_existing_values_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OLLAMA_TIMEOUT_SECONDS=999\n", encoding="utf-8")

            previous = os.environ.get("OLLAMA_TIMEOUT_SECONDS")
            try:
                os.environ["OLLAMA_TIMEOUT_SECONDS"] = "120"
                load_env_file(env_path, override=False)
                self.assertEqual(os.environ["OLLAMA_TIMEOUT_SECONDS"], "120")
                load_env_file(env_path, override=True)
                self.assertEqual(os.environ["OLLAMA_TIMEOUT_SECONDS"], "999")
            finally:
                if previous is None:
                    os.environ.pop("OLLAMA_TIMEOUT_SECONDS", None)
                else:
                    os.environ["OLLAMA_TIMEOUT_SECONDS"] = previous

    def test_read_bool_env_supports_truthy_and_default_values(self) -> None:
        previous = os.environ.get("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT")
        try:
            os.environ["PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"] = "yes"
            self.assertTrue(read_bool_env("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"))

            os.environ["PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"] = "off"
            self.assertFalse(read_bool_env("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"))

            os.environ.pop("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT", None)
            self.assertTrue(
                read_bool_env(
                    "PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT",
                    default=True,
                )
            )
        finally:
            if previous is None:
                os.environ.pop("PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT", None)
            else:
                os.environ["PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT"] = previous


if __name__ == "__main__":
    unittest.main()

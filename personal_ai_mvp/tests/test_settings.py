from __future__ import annotations

import os
import unittest
from pathlib import Path

from infrastructure.config.settings import get_settings, project_root_path


class SettingsTests(unittest.TestCase):
    def test_settings_use_env_overrides_for_urls_paths_and_names(self) -> None:
        previous = {
            key: os.environ.get(key)
            for key in (
                "OLLAMA_BASE_URL",
                "OLLAMA_TIMEOUT_SECONDS",
                "PERSONAL_AI_OLLAMA_NUM_CTX_BY_MODEL",
                "OPENAI_API_KEY",
                "OPENAI_BASE_URL",
                "OPENAI_TIMEOUT_SECONDS",
                "PERSONAL_AI_OPENAI_MODELS",
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                "PERSONAL_AI_WEB_SEARCH_BASE_URL",
                "PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS",
                "PERSONAL_AI_WEB_SEARCH_MAX_RESULTS",
                "PERSONAL_AI_WEB_SEARCH_MAX_QUERY_CHARS",
                "PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS",
                "PERSONAL_AI_WEB_SEARCH_BLOCKED_DOMAINS",
                "PERSONAL_AI_DEBUG_API_ERRORS",
                "PERSONAL_AI_SERIALIZE_OLLAMA_REQUESTS",
                "PERSONAL_AI_DEFAULT_MODEL",
                "PERSONAL_AI_AGENT_DEFAULT_MODEL",
                "PERSONAL_AI_UI_HOST",
                "PERSONAL_AI_UI_PORT",
                "PERSONAL_AI_UI_DEV_HOST",
                "PERSONAL_AI_UI_DEV_PORT",
                "PERSONAL_AI_UI_DEV_API_TARGET",
                "PERSONAL_AI_STATE_DIR_NAME",
                "PERSONAL_AI_HISTORY_DB_NAME",
                "PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME",
                "PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME",
                "PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME",
                "PERSONAL_AI_EVAL_HISTORY_PATH",
            )
        }
        try:
            os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:22445"
            os.environ["OLLAMA_TIMEOUT_SECONDS"] = "222"
            os.environ["PERSONAL_AI_OLLAMA_NUM_CTX_BY_MODEL"] = "gpt-oss=2048,qwen2.5=8192"
            os.environ["OPENAI_API_KEY"] = "test-key"
            os.environ["OPENAI_BASE_URL"] = "https://api.openai.example/v1"
            os.environ["OPENAI_TIMEOUT_SECONDS"] = "77"
            os.environ["PERSONAL_AI_OPENAI_MODELS"] = "gpt-5.5,gpt-5-mini"
            os.environ["PERSONAL_AI_WEB_SEARCH_PROVIDER"] = "searxng"
            os.environ["PERSONAL_AI_WEB_SEARCH_BASE_URL"] = "http://127.0.0.1:8899"
            os.environ["PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS"] = "31"
            os.environ["PERSONAL_AI_WEB_SEARCH_MAX_RESULTS"] = "9"
            os.environ["PERSONAL_AI_WEB_SEARCH_MAX_QUERY_CHARS"] = "280"
            os.environ["PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS"] = "docs.python.org,openai.com"
            os.environ["PERSONAL_AI_WEB_SEARCH_BLOCKED_DOMAINS"] = "ads.docs.python.org,tracker.example"
            os.environ["PERSONAL_AI_DEBUG_API_ERRORS"] = "true"
            os.environ["PERSONAL_AI_SERIALIZE_OLLAMA_REQUESTS"] = "false"
            os.environ["PERSONAL_AI_DEFAULT_MODEL"] = "qwen2.5-coder:7b"
            os.environ["PERSONAL_AI_AGENT_DEFAULT_MODEL"] = "gemma3:4b"
            os.environ["PERSONAL_AI_UI_HOST"] = "0.0.0.0"
            os.environ["PERSONAL_AI_UI_PORT"] = "9900"
            os.environ["PERSONAL_AI_UI_DEV_HOST"] = "localhost"
            os.environ["PERSONAL_AI_UI_DEV_PORT"] = "5511"
            os.environ["PERSONAL_AI_UI_DEV_API_TARGET"] = "http://127.0.0.1:9900"
            os.environ["PERSONAL_AI_STATE_DIR_NAME"] = ".pa_state"
            os.environ["PERSONAL_AI_HISTORY_DB_NAME"] = "history.db"
            os.environ["PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME"] = "drafts"
            os.environ["PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME"] = "scaffold_root"
            os.environ["PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME"] = "probe_root"
            os.environ["PERSONAL_AI_EVAL_HISTORY_PATH"] = "custom/eval.jsonl"

            settings = get_settings()

            self.assertEqual(settings.ollama_base_url, "http://127.0.0.1:22445")
            self.assertEqual(settings.ollama_timeout_seconds, 222)
            self.assertEqual(
                settings.ollama_num_ctx_by_model,
                (("gpt-oss", 2048), ("qwen2.5", 8192)),
            )
            self.assertEqual(settings.openai_api_key, "test-key")
            self.assertEqual(settings.openai_base_url, "https://api.openai.example/v1")
            self.assertEqual(settings.openai_timeout_seconds, 77)
            self.assertEqual(settings.openai_models, ("gpt-5.5", "gpt-5-mini"))
            self.assertEqual(settings.web_search_provider, "searxng")
            self.assertEqual(settings.web_search_base_url, "http://127.0.0.1:8899")
            self.assertEqual(settings.web_search_timeout_seconds, 31)
            self.assertEqual(settings.web_search_max_results, 9)
            self.assertEqual(settings.web_search_max_query_chars, 280)
            self.assertEqual(
                settings.web_search_allowed_domains,
                ("docs.python.org", "openai.com"),
            )
            self.assertEqual(
                settings.web_search_blocked_domains,
                ("ads.docs.python.org", "tracker.example"),
            )
            self.assertTrue(settings.debug_api_errors)
            self.assertFalse(settings.serialize_ollama_requests)
            self.assertEqual(settings.default_model, "qwen2.5-coder:7b")
            self.assertEqual(settings.agent_default_model, "gemma3:4b")
            self.assertEqual(settings.ui_host, "0.0.0.0")
            self.assertEqual(settings.ui_port, 9900)
            self.assertEqual(settings.ui_dev_host, "localhost")
            self.assertEqual(settings.ui_dev_port, 5511)
            self.assertEqual(settings.ui_dev_api_target, "http://127.0.0.1:9900")
            self.assertEqual(settings.state_dir_name, ".pa_state")
            self.assertEqual(settings.history_db_name, "history.db")
            self.assertEqual(settings.agent_runtime_drafts_dir_name, "drafts")
            self.assertEqual(settings.runtime_scaffold_dir_name, "scaffold_root")
            self.assertEqual(settings.runtime_write_probe_dir_name, "probe_root")
            self.assertEqual(settings.eval_history_path, project_root_path() / "custom" / "eval.jsonl")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_settings_build_vault_relative_runtime_paths(self) -> None:
        previous_state_dir = os.environ.get("PERSONAL_AI_STATE_DIR_NAME")
        previous_history_name = os.environ.get("PERSONAL_AI_HISTORY_DB_NAME")
        previous_drafts_name = os.environ.get("PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME")
        try:
            os.environ["PERSONAL_AI_STATE_DIR_NAME"] = ".runtime_state"
            os.environ["PERSONAL_AI_HISTORY_DB_NAME"] = "queries.sqlite3"
            os.environ["PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME"] = "draft_bank"
            settings = get_settings()
            vault_root = Path("H:/Vault")

            self.assertEqual(settings.state_dir_path(vault_root), vault_root / ".runtime_state")
            self.assertEqual(
                settings.history_db_path(vault_root),
                vault_root / ".runtime_state" / "queries.sqlite3",
            )
            self.assertEqual(
                settings.runtime_drafts_path(vault_root),
                vault_root / ".runtime_state" / "draft_bank",
            )
        finally:
            if previous_state_dir is None:
                os.environ.pop("PERSONAL_AI_STATE_DIR_NAME", None)
            else:
                os.environ["PERSONAL_AI_STATE_DIR_NAME"] = previous_state_dir
            if previous_history_name is None:
                os.environ.pop("PERSONAL_AI_HISTORY_DB_NAME", None)
            else:
                os.environ["PERSONAL_AI_HISTORY_DB_NAME"] = previous_history_name
            if previous_drafts_name is None:
                os.environ.pop("PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME", None)
            else:
                os.environ["PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME"] = previous_drafts_name

    def test_runtime_scaffold_and_probe_defaults_are_hidden_under_runtime(self) -> None:
        previous_scaffold = os.environ.get("PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME")
        previous_probe = os.environ.get("PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME")
        try:
            os.environ.pop("PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME", None)
            os.environ.pop("PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME", None)

            settings = get_settings()

            self.assertEqual(settings.runtime_scaffold_dir_name, ".runtime/runtime_scaffold")
            self.assertEqual(settings.runtime_write_probe_dir_name, ".runtime/runtime_write_probe")
        finally:
            if previous_scaffold is None:
                os.environ.pop("PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME", None)
            else:
                os.environ["PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME"] = previous_scaffold
            if previous_probe is None:
                os.environ.pop("PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME", None)
            else:
                os.environ["PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME"] = previous_probe

    def test_agent_default_model_falls_back_to_planner_override_when_not_explicitly_set(self) -> None:
        previous_agent_default = os.environ.get("PERSONAL_AI_AGENT_DEFAULT_MODEL")
        previous_planner = os.environ.get("PERSONAL_AI_AGENT_PLANNER_MODEL")
        try:
            os.environ.pop("PERSONAL_AI_AGENT_DEFAULT_MODEL", None)
            os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = "deepseek-r1:8b"

            settings = get_settings()

            self.assertEqual(settings.agent_default_model, "deepseek-r1:8b")
        finally:
            if previous_agent_default is None:
                os.environ.pop("PERSONAL_AI_AGENT_DEFAULT_MODEL", None)
            else:
                os.environ["PERSONAL_AI_AGENT_DEFAULT_MODEL"] = previous_agent_default
            if previous_planner is None:
                os.environ.pop("PERSONAL_AI_AGENT_PLANNER_MODEL", None)
            else:
                os.environ["PERSONAL_AI_AGENT_PLANNER_MODEL"] = previous_planner

    def test_settings_project_relative_paths_use_personal_ai_home_when_configured(self) -> None:
        previous_home = os.environ.get("PERSONAL_AI_HOME")
        previous_eval_path = os.environ.get("PERSONAL_AI_EVAL_HISTORY_PATH")
        previous_training_dir = os.environ.get("PERSONAL_AI_TRAINING_EXAMPLES_DIR")
        try:
            os.environ["PERSONAL_AI_HOME"] = "H:/Projects/PersonalAI/personal_ai_mvp"
            os.environ["PERSONAL_AI_EVAL_HISTORY_PATH"] = "custom/eval.jsonl"
            os.environ["PERSONAL_AI_TRAINING_EXAMPLES_DIR"] = "assets/training"

            settings = get_settings()

            self.assertEqual(
                settings.eval_history_path,
                Path("H:/Projects/PersonalAI/personal_ai_mvp/custom/eval.jsonl").resolve(),
            )
            self.assertEqual(
                settings.training_examples_dir,
                Path("H:/Projects/PersonalAI/personal_ai_mvp/assets/training").resolve(),
            )
        finally:
            if previous_home is None:
                os.environ.pop("PERSONAL_AI_HOME", None)
            else:
                os.environ["PERSONAL_AI_HOME"] = previous_home
            if previous_eval_path is None:
                os.environ.pop("PERSONAL_AI_EVAL_HISTORY_PATH", None)
            else:
                os.environ["PERSONAL_AI_EVAL_HISTORY_PATH"] = previous_eval_path
            if previous_training_dir is None:
                os.environ.pop("PERSONAL_AI_TRAINING_EXAMPLES_DIR", None)
            else:
                os.environ["PERSONAL_AI_TRAINING_EXAMPLES_DIR"] = previous_training_dir


if __name__ == "__main__":
    unittest.main()

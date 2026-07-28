"""Runtime configuration infrastructure."""

from infrastructure.config.env_loader import (
    default_env_file_path,
    load_env_file,
    read_bool_env,
)
from infrastructure.config.settings import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    DEFAULT_PERSONAL_AI_MODEL,
    DEFAULT_UI_DEV_PORT,
    DEFAULT_UI_HOST,
    DEFAULT_UI_PORT,
    PersonalAISettings,
    default_ollama_fallback_base_urls,
    get_settings,
    project_root_path,
)

__all__ = [
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_TIMEOUT_SECONDS",
    "DEFAULT_OPENAI_BASE_URL",
    "DEFAULT_OPENAI_TIMEOUT_SECONDS",
    "DEFAULT_PERSONAL_AI_MODEL",
    "DEFAULT_UI_DEV_PORT",
    "DEFAULT_UI_HOST",
    "DEFAULT_UI_PORT",
    "PersonalAISettings",
    "default_env_file_path",
    "default_ollama_fallback_base_urls",
    "get_settings",
    "load_env_file",
    "project_root_path",
    "read_bool_env",
]

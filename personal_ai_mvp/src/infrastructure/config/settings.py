"""Centralized runtime settings for PersonalAI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from infrastructure.config.env_loader import load_env_file, read_bool_env

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11435"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 1800
DEFAULT_PERSONAL_AI_MODEL = "gemma:latest"
DEFAULT_AGENT_MODEL = "qwen2.5-coder:7b"
DEFAULT_UI_HOST = "127.0.0.1"
DEFAULT_UI_PORT = 8765
DEFAULT_UI_DEV_PORT = 5173
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 180
DEFAULT_DEBUG_API_ERRORS = False
DEFAULT_WEB_SEARCH_PROVIDER = "disabled"
DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS = 20
DEFAULT_WEB_SEARCH_MAX_RESULTS = 5
DEFAULT_WEB_SEARCH_MAX_QUERY_CHARS = 400


def _fallback_project_root_path() -> Path:
    """Return the checkout-relative project root used as the final fallback."""
    return Path(__file__).resolve().parents[3]


def project_root_path(env_file_path: Path | None = None) -> Path:
    """Return the effective PersonalAI home directory for project-relative assets."""
    explicit_root = (
        os.getenv("PERSONAL_AI_HOME", "").strip()
        or os.getenv("PERSONAL_AI_PROJECT_ROOT", "").strip()
    )
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    if env_file_path is not None:
        return env_file_path.expanduser().resolve().parent
    return _fallback_project_root_path()


def _read_str(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _read_csv(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return ()
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


def _read_model_int_overrides(
    name: str,
    default_items: tuple[tuple[str, int], ...] = (),
) -> tuple[tuple[str, int], ...]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default_items
    overrides: list[tuple[str, int]] = []
    for raw_item in raw_value.split(","):
        item = raw_item.strip()
        if not item or "=" not in item:
            continue
        prefix, raw_int = item.split("=", 1)
        prefix = prefix.strip()
        raw_int = raw_int.strip()
        if not prefix or not raw_int:
            continue
        try:
            value = int(raw_int)
        except ValueError:
            continue
        if value > 0:
            overrides.append((prefix, value))
    return tuple(overrides) or default_items


def _project_relative_path(
    name: str,
    default_relative: str,
    *,
    project_root: Path,
) -> Path:
    raw_value = _read_str(name, default_relative)
    candidate = Path(raw_value)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _path_tuple(name: str, defaults: tuple[str, ...]) -> tuple[Path, ...]:
    values = _read_csv(name)
    if not values:
        return tuple(Path(item) for item in defaults)
    return tuple(Path(item) for item in values)


def _replace_url_port(base_url: str, port: int) -> str | None:
    parsed = urlsplit(base_url)
    hostname = parsed.hostname
    if not hostname:
        return None
    if ":" in hostname and not hostname.startswith("["):
        netloc = f"[{hostname}]"
    else:
        netloc = hostname
    if parsed.port == port:
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")
    netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)).rstrip("/")


def default_ollama_fallback_base_urls(base_url: str) -> tuple[str, ...]:
    """Return built-in fallback Ollama URLs derived from the configured base URL."""
    candidates = (
        _replace_url_port(base_url, 11434),
        _replace_url_port(base_url, 11435),
        "http://127.0.0.1:11434",
        DEFAULT_OLLAMA_BASE_URL,
    )
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class PersonalAISettings:
    """Typed environment-backed settings for PersonalAI."""

    ollama_base_url: str
    ollama_timeout_seconds: int
    ollama_fallback_base_urls: tuple[str, ...]
    ollama_num_ctx_by_model: tuple[tuple[str, int], ...]
    openai_api_key: str | None
    openai_base_url: str
    openai_timeout_seconds: int
    openai_models: tuple[str, ...]
    web_search_provider: str
    web_search_base_url: str | None
    web_search_timeout_seconds: int
    web_search_max_results: int
    web_search_max_query_chars: int
    web_search_allowed_domains: tuple[str, ...]
    web_search_blocked_domains: tuple[str, ...]
    debug_api_errors: bool
    serialize_ollama_requests: bool
    prompt_preprocessor_mode: str
    prompt_translation_model: str | None
    prompt_translation_fallback_model: str | None
    default_model: str
    agent_default_model: str
    ui_host: str
    ui_port: int
    ui_dev_host: str
    ui_dev_port: int
    ui_dev_api_target: str
    state_dir_name: str
    history_db_name: str
    agent_runtime_drafts_dir_name: str
    runtime_scaffold_dir_name: str
    runtime_write_probe_dir_name: str
    restricted_note_prefixes: tuple[Path, ...]
    training_examples_dir: Path
    curated_examples_dir: Path
    ukrainian_examples_dir: Path
    eval_history_path: Path
    eval_compare_history_path: Path
    benchmark_pack_path: Path
    fine_tune_bundles_dir: Path
    frontend_dist_dir: Path
    agent_recursive_refinement: bool
    agent_multi_model_discussion: bool
    chat_recursive_refinement: bool
    global_recursive_refinement: bool
    agent_planner_model: str | None
    agent_executor_model: str | None
    agent_critic_model: str | None
    agent_synthesis_model: str | None
    agent_approver_model: str | None
    agent_discussion_preset: str | None

    @classmethod
    def from_env(cls) -> PersonalAISettings:
        """Build settings from the current environment and project-local .env file."""
        env_file_path = load_env_file()
        project_root = project_root_path(env_file_path)
        global_recursive_refinement = read_bool_env("PERSONAL_AI_RECURSIVE_REFINEMENT", default=False)
        training_examples_dir = _project_relative_path(
            "PERSONAL_AI_TRAINING_EXAMPLES_DIR",
            "training_examples",
            project_root=project_root,
        )
        agent_planner_model = _read_str("PERSONAL_AI_AGENT_PLANNER_MODEL", "") or None
        return cls(
            ollama_base_url=_read_str("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            ollama_timeout_seconds=_read_int("OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS),
            ollama_fallback_base_urls=_read_csv("OLLAMA_FALLBACK_BASE_URLS"),
            ollama_num_ctx_by_model=_read_model_int_overrides(
                "PERSONAL_AI_OLLAMA_NUM_CTX_BY_MODEL",
                default_items=(("gpt-oss", 2048),),
            ),
            openai_api_key=_read_str("OPENAI_API_KEY", "") or None,
            openai_base_url=_read_str("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
            openai_timeout_seconds=_read_int("OPENAI_TIMEOUT_SECONDS", DEFAULT_OPENAI_TIMEOUT_SECONDS),
            openai_models=_read_csv("PERSONAL_AI_OPENAI_MODELS"),
            web_search_provider=_read_str(
                "PERSONAL_AI_WEB_SEARCH_PROVIDER",
                DEFAULT_WEB_SEARCH_PROVIDER,
            ).lower(),
            web_search_base_url=_read_str("PERSONAL_AI_WEB_SEARCH_BASE_URL", "") or None,
            web_search_timeout_seconds=_read_int(
                "PERSONAL_AI_WEB_SEARCH_TIMEOUT_SECONDS",
                DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS,
            ),
            web_search_max_results=_read_int(
                "PERSONAL_AI_WEB_SEARCH_MAX_RESULTS",
                DEFAULT_WEB_SEARCH_MAX_RESULTS,
            ),
            web_search_max_query_chars=_read_int(
                "PERSONAL_AI_WEB_SEARCH_MAX_QUERY_CHARS",
                DEFAULT_WEB_SEARCH_MAX_QUERY_CHARS,
            ),
            web_search_allowed_domains=_read_csv("PERSONAL_AI_WEB_SEARCH_ALLOWED_DOMAINS"),
            web_search_blocked_domains=_read_csv("PERSONAL_AI_WEB_SEARCH_BLOCKED_DOMAINS"),
            debug_api_errors=read_bool_env(
                "PERSONAL_AI_DEBUG_API_ERRORS",
                default=DEFAULT_DEBUG_API_ERRORS,
            ),
            serialize_ollama_requests=read_bool_env(
                "PERSONAL_AI_SERIALIZE_OLLAMA_REQUESTS",
                default=True,
            ),
            prompt_preprocessor_mode=_read_str(
                "PERSONAL_AI_PROMPT_PREPROCESSOR_MODE",
                "disabled",
            ).lower(),
            prompt_translation_model=_read_str(
                "PERSONAL_AI_PROMPT_TRANSLATION_MODEL",
                "",
            )
            or None,
            prompt_translation_fallback_model=_read_str(
                "PERSONAL_AI_PROMPT_TRANSLATION_FALLBACK_MODEL",
                "",
            )
            or None,
            default_model=_read_str("PERSONAL_AI_DEFAULT_MODEL", DEFAULT_PERSONAL_AI_MODEL),
            agent_default_model=_read_str(
                "PERSONAL_AI_AGENT_DEFAULT_MODEL",
                agent_planner_model or DEFAULT_AGENT_MODEL,
            ),
            ui_host=_read_str("PERSONAL_AI_UI_HOST", DEFAULT_UI_HOST),
            ui_port=_read_int("PERSONAL_AI_UI_PORT", DEFAULT_UI_PORT),
            ui_dev_host=_read_str("PERSONAL_AI_UI_DEV_HOST", DEFAULT_UI_HOST),
            ui_dev_port=_read_int("PERSONAL_AI_UI_DEV_PORT", DEFAULT_UI_DEV_PORT),
            ui_dev_api_target=_read_str("PERSONAL_AI_UI_DEV_API_TARGET", f"http://{DEFAULT_UI_HOST}:{DEFAULT_UI_PORT}"),
            state_dir_name=_read_str("PERSONAL_AI_STATE_DIR_NAME", ".personal_ai"),
            history_db_name=_read_str("PERSONAL_AI_HISTORY_DB_NAME", "query_history.sqlite3"),
            agent_runtime_drafts_dir_name=_read_str(
                "PERSONAL_AI_AGENT_RUNTIME_DRAFTS_DIR_NAME",
                "agent_runtime_drafts",
            ),
            runtime_scaffold_dir_name=_read_str(
                "PERSONAL_AI_AGENT_RUNTIME_SCAFFOLD_DIR_NAME",
                ".runtime/runtime_scaffold",
            ),
            runtime_write_probe_dir_name=_read_str(
                "PERSONAL_AI_AGENT_RUNTIME_WRITE_PROBE_DIR_NAME",
                ".runtime/runtime_write_probe",
            ),
            restricted_note_prefixes=_path_tuple(
                "PERSONAL_AI_RESTRICTED_NOTE_PREFIXES",
                (
                    ".personal_ai",
                    ".obsidian",
                    ".trash",
                    ".history",
                ),
            ),
            training_examples_dir=training_examples_dir,
            curated_examples_dir=_project_relative_path(
                "PERSONAL_AI_CURATED_EXAMPLES_DIR",
                "training_examples/curated",
                project_root=project_root,
            ),
            ukrainian_examples_dir=_project_relative_path(
                "PERSONAL_AI_UKRAINIAN_EXAMPLES_DIR",
                "training_examples/ukrainian",
                project_root=project_root,
            ),
            eval_history_path=_project_relative_path(
                "PERSONAL_AI_EVAL_HISTORY_PATH",
                "training_examples/eval_history.jsonl",
                project_root=project_root,
            ),
            eval_compare_history_path=_project_relative_path(
                "PERSONAL_AI_EVAL_COMPARE_HISTORY_PATH",
                "training_examples/eval_compare_history.jsonl",
                project_root=project_root,
            ),
            benchmark_pack_path=_project_relative_path(
                "PERSONAL_AI_BENCHMARK_PACK_PATH",
                "training_examples/benchmarks/repo_aware_pack.json",
                project_root=project_root,
            ),
            fine_tune_bundles_dir=_project_relative_path(
                "PERSONAL_AI_FINE_TUNE_BUNDLES_DIR",
                "training_examples/fine_tune",
                project_root=project_root,
            ),
            frontend_dist_dir=_project_relative_path(
                "PERSONAL_AI_FRONTEND_DIST_DIR",
                "frontend/dist",
                project_root=project_root,
            ),
            agent_recursive_refinement=read_bool_env(
                "PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT",
                default=global_recursive_refinement,
            ),
            agent_multi_model_discussion=read_bool_env(
                "PERSONAL_AI_AGENT_MULTI_MODEL_DISCUSSION",
                default=True,
            ),
            chat_recursive_refinement=read_bool_env(
                "PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT",
                default=global_recursive_refinement,
            ),
            global_recursive_refinement=global_recursive_refinement,
            agent_planner_model=agent_planner_model,
            agent_executor_model=_read_str("PERSONAL_AI_AGENT_EXECUTOR_MODEL", "") or None,
            agent_critic_model=_read_str("PERSONAL_AI_AGENT_CRITIC_MODEL", "") or None,
            agent_synthesis_model=_read_str("PERSONAL_AI_AGENT_SYNTHESIS_MODEL", "") or None,
            agent_approver_model=_read_str("PERSONAL_AI_AGENT_APPROVER_MODEL", "") or None,
            agent_discussion_preset=_read_str("PERSONAL_AI_AGENT_DISCUSSION_PRESET", "").lower() or None,
        )

    def state_dir_path(self, vault_root: Path) -> Path:
        """Return the PersonalAI state directory inside the vault."""
        return vault_root / self.state_dir_name

    def history_db_path(self, vault_root: Path) -> Path:
        """Return the default SQLite history path inside the vault."""
        return self.state_dir_path(vault_root) / self.history_db_name

    def runtime_drafts_path(self, vault_root: Path) -> Path:
        """Return the directory used for persisted runtime drafts."""
        return self.state_dir_path(vault_root) / self.agent_runtime_drafts_dir_name


def get_settings() -> PersonalAISettings:
    """Return a fresh snapshot of environment-backed PersonalAI settings."""
    return PersonalAISettings.from_env()


__all__ = [
    "DEFAULT_AGENT_MODEL",
    "DEFAULT_DEBUG_API_ERRORS",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_TIMEOUT_SECONDS",
    "DEFAULT_OPENAI_BASE_URL",
    "DEFAULT_OPENAI_TIMEOUT_SECONDS",
    "DEFAULT_PERSONAL_AI_MODEL",
    "DEFAULT_UI_DEV_PORT",
    "DEFAULT_UI_HOST",
    "DEFAULT_UI_PORT",
    "DEFAULT_WEB_SEARCH_MAX_RESULTS",
    "DEFAULT_WEB_SEARCH_MAX_QUERY_CHARS",
    "DEFAULT_WEB_SEARCH_PROVIDER",
    "DEFAULT_WEB_SEARCH_TIMEOUT_SECONDS",
    "PersonalAISettings",
    "default_ollama_fallback_base_urls",
    "get_settings",
    "project_root_path",
]

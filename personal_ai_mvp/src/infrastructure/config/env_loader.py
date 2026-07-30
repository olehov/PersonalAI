"""Lightweight .env loader for local runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path


def _fallback_project_root_path() -> Path:
    """Return the checkout-relative project root used as the final fallback."""
    return Path(__file__).resolve().parents[3]


def _search_parent_env_file(start: Path) -> Path | None:
    """Search one directory chain for the first existing .env file."""
    current = start.resolve()
    for candidate_dir in (current, *current.parents):
        candidate = candidate_dir / ".env"
        if candidate.exists():
            return candidate
    return None


def default_env_file_path() -> Path:
    """Return the default .env file path using explicit home, cwd, then checkout fallback."""
    explicit_env_file = os.getenv("PERSONAL_AI_ENV_FILE", "").strip()
    if explicit_env_file:
        return Path(explicit_env_file).expanduser()

    explicit_home = (
        os.getenv("PERSONAL_AI_HOME", "").strip()
        or os.getenv("PERSONAL_AI_PROJECT_ROOT", "").strip()
    )
    if explicit_home:
        return Path(explicit_home).expanduser() / ".env"

    discovered = _search_parent_env_file(Path.cwd())
    if discovered is not None:
        return discovered

    return _fallback_project_root_path() / ".env"


def load_env_file(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""
    env_path = path if path is not None else default_env_file_path()
    if not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if not key:
            continue
        if key in os.environ and not override:
            continue
        os.environ[key] = value

    return env_path


def read_bool_env(name: str, *, default: bool = False) -> bool:
    """Read a boolean environment variable using common truthy string values."""
    raw_value = os.getenv(name, "").strip().casefold()
    if not raw_value:
        return default
    return raw_value in {"1", "true", "yes", "on"}


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


__all__ = [
    "default_env_file_path",
    "load_env_file",
    "read_bool_env",
]

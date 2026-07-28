"""CLI application package for PersonalAI."""

from cli_app.main import build_parser, default_history_db_path, main
from cli_app.runtime import CliRuntime, build_cli_runtime

__all__ = [
    "CliRuntime",
    "build_cli_runtime",
    "build_parser",
    "default_history_db_path",
    "main",
]

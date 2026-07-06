"""Command-line interface for exploring an Obsidian vault."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from personal_ai.application import (
    AgentRuntimeService,
    BenchmarkRunService,
    ChatService,
    NoteDraftService,
    TrainingEvalService,
    TrainingFineTuneService,
)
from personal_ai.cli_command_handlers import (
    handle_basic_command,
    handle_benchmark_command,
    handle_maintenance_command,
    handle_note_command,
    handle_training_command,
)
from personal_ai.cli_parser_builders import (
    add_basic_parsers,
    add_benchmark_parsers,
    add_maintenance_parsers,
    add_note_parsers,
    add_training_parsers,
)
from personal_ai.cli_runtime import build_cli_runtime
from personal_ai.infrastructure.ollama_client import OllamaClient
from personal_ai.infrastructure.env_loader import load_env_file

load_env_file()

DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
DEFAULT_OLLAMA_MODEL = os.getenv("PERSONAL_AI_DEFAULT_MODEL", "llama3:latest")


DEFAULT_EVAL_HISTORY_PATH = (
    Path(__file__).resolve().parents[2] / "training_examples" / "eval_history.jsonl"
)
DEFAULT_COMPARE_HISTORY_PATH = (
    Path(__file__).resolve().parents[2] / "training_examples" / "eval_compare_history.jsonl"
)
DEFAULT_BENCHMARK_PACK_PATH = (
    Path(__file__).resolve().parents[2]
    / "training_examples"
    / "benchmarks"
    / "repo_aware_pack.json"
)
DEFAULT_FINE_TUNE_BUNDLES_DIR = (
    Path(__file__).resolve().parents[2] / "training_examples" / "fine_tune"
)


def default_history_db_path(vault_root: Path) -> Path:
    """Return the default SQLite history location for the given vault."""
    return vault_root / ".personal_ai" / "query_history.sqlite3"


def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser."""
    parser = argparse.ArgumentParser(description="PersonalAI Obsidian vault CLI")
    parser.add_argument(
        "--vault",
        type=Path,
        required=True,
        help="Path to the Obsidian vault root.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--history-db",
        type=Path,
        help="Optional SQLite path for persisted ask history.",
    )
    parser.add_argument(
        "--ollama-timeout-seconds",
        type=int,
        help="Optional timeout for Ollama HTTP calls in seconds. Overrides OLLAMA_TIMEOUT_SECONDS.",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help="Base URL for the local Ollama server. Overrides OLLAMA_BASE_URL.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_basic_parsers(
        subparsers,
        default_model=DEFAULT_OLLAMA_MODEL,
    )
    add_benchmark_parsers(
        subparsers,
        default_model=DEFAULT_OLLAMA_MODEL,
        default_benchmark_pack_path=DEFAULT_BENCHMARK_PACK_PATH,
    )
    add_note_parsers(
        subparsers,
        add_note_mutation_arguments=_add_note_mutation_arguments,
        add_note_draft_arguments=_add_note_draft_arguments,
    )
    add_maintenance_parsers(
        subparsers,
        default_model=DEFAULT_OLLAMA_MODEL,
        add_maintenance_draft_arguments=_add_maintenance_draft_arguments,
    )
    add_training_parsers(
        subparsers,
        default_model=DEFAULT_OLLAMA_MODEL,
        default_eval_history_path=DEFAULT_EVAL_HISTORY_PATH,
        default_compare_history_path=DEFAULT_COMPARE_HISTORY_PATH,
        default_fine_tune_bundles_dir=DEFAULT_FINE_TUNE_BUNDLES_DIR,
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = build_cli_runtime(
        vault_root=args.vault,
        history_db_path=(
            args.history_db if args.history_db is not None else default_history_db_path(args.vault)
        ),
        ollama_base_url=args.ollama_base_url,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
    )

    for handler in (
        lambda: handle_basic_command(args, runtime),
        lambda: handle_benchmark_command(args, runtime),
        lambda: handle_note_command(args, runtime, read_content_input=_read_content_input),
        lambda: handle_maintenance_command(args, runtime),
        lambda: handle_training_command(args, runtime),
    ):
        result = handler()
        if result is not None:
            return result

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_note_mutation_arguments(parser: argparse.ArgumentParser, *, include_approval: bool) -> None:
    parser.add_argument("--title", required=True, help="Note title.")
    parser.add_argument(
        "--content-file",
        type=Path,
        required=True,
        help="Path to a UTF-8 markdown content file.",
    )
    parser.add_argument(
        "--action",
        choices=("auto", "create", "update", "refactor", "archive"),
        default="auto",
        help="Requested mutation type.",
    )
    parser.add_argument("--target-dir", help="Relative vault directory for new note creation.")
    parser.add_argument("--target-path", help="Explicit relative note path.")
    if include_approval:
        parser.add_argument(
            "--approve",
            action="store_true",
            help="Explicitly approve applying the change.",
        )


def _add_note_draft_arguments(parser: argparse.ArgumentParser, *, include_approval: bool) -> None:
    parser.add_argument("--title", required=True, help="Note title.")
    parser.add_argument("--instruction", required=True, help="What the note should contain or how it should change.")
    parser.add_argument(
        "--action",
        choices=("auto", "create", "update", "refactor", "archive"),
        default="auto",
        help="Requested mutation type.",
    )
    parser.add_argument("--target-dir", help="Relative vault directory for new note creation.")
    parser.add_argument("--target-path", help="Explicit relative note path.")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model name to use.")
    parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories for draft grounding.",
    )
    if include_approval:
        parser.add_argument(
            "--approve",
            action="store_true",
            help="Explicitly approve applying the generated change.",
        )


def _add_maintenance_draft_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_approval: bool,
) -> None:
    parser.add_argument("--note", required=True, help="Note title or relative path with a maintenance finding.")
    parser.add_argument(
        "--kind",
        choices=("empty_note", "sparse_note", "isolated_note", "duplicate_title"),
        help="Optional maintenance finding kind to target.",
    )
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model name to use.")
    if include_approval:
        parser.add_argument(
            "--approve",
            action="store_true",
            help="Explicitly approve applying the generated change.",
        )


def _read_content_input(args: argparse.Namespace) -> str:
    return args.content_file.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI bootstrap for exploring an Obsidian vault."""

from __future__ import annotations

import argparse
from pathlib import Path

from cli_app.argument_helpers import (
    add_maintenance_draft_arguments,
    add_note_draft_arguments,
    add_note_mutation_arguments,
    default_history_db_path,
    read_content_input,
)
from cli_app.dispatch import dispatch_cli_command
from cli_app.parser_builders import (
    add_basic_parsers,
    add_benchmark_parsers,
    add_maintenance_parsers,
    add_note_parsers,
    add_training_parsers,
)
from cli_app.runtime import build_cli_runtime
from infrastructure.config.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    settings = get_settings()
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
        default=settings.ollama_base_url,
        help="Base URL for the local Ollama server. Overrides OLLAMA_BASE_URL.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_basic_parsers(
        subparsers,
        default_model=settings.default_model,
    )
    add_benchmark_parsers(
        subparsers,
        default_model=settings.default_model,
        default_benchmark_pack_path=settings.benchmark_pack_path,
    )
    add_note_parsers(
        subparsers,
        add_note_mutation_arguments=add_note_mutation_arguments,
        add_note_draft_arguments=add_note_draft_arguments,
    )
    add_maintenance_parsers(
        subparsers,
        default_model=settings.default_model,
        add_maintenance_draft_arguments=add_maintenance_draft_arguments,
    )
    add_training_parsers(
        subparsers,
        default_model=settings.default_model,
        default_eval_history_path=settings.eval_history_path,
        default_compare_history_path=settings.eval_compare_history_path,
        default_fine_tune_bundles_dir=settings.fine_tune_bundles_dir,
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
    result = dispatch_cli_command(
        args,
        runtime,
        read_content_input=read_content_input,
    )
    if result is not None:
        return result

    parser.error(f"Unsupported command: {args.command}")
    return 2


__all__ = [
    "build_parser",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())

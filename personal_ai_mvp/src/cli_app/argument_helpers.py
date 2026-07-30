"""Argument and input helpers for the PersonalAI CLI entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from infrastructure.config.settings import get_settings


def default_history_db_path(vault_root: Path) -> Path:
    """Return the default SQLite history location for the given vault."""
    return get_settings().history_db_path(vault_root)


def add_note_mutation_arguments(parser: argparse.ArgumentParser, *, include_approval: bool) -> None:
    """Register shared note-mutation arguments."""
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


def add_note_draft_arguments(parser: argparse.ArgumentParser, *, include_approval: bool) -> None:
    """Register shared note-draft arguments."""
    settings = get_settings()
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
    parser.add_argument("--model", default=settings.default_model, help="Ollama model name to use.")
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


def add_maintenance_draft_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_approval: bool,
) -> None:
    """Register shared maintenance-draft arguments."""
    settings = get_settings()
    parser.add_argument("--note", required=True, help="Note title or relative path with a maintenance finding.")
    parser.add_argument(
        "--kind",
        choices=("empty_note", "sparse_note", "isolated_note", "duplicate_title"),
        help="Optional maintenance finding kind to target.",
    )
    parser.add_argument("--model", default=settings.default_model, help="Ollama model name to use.")
    if include_approval:
        parser.add_argument(
            "--approve",
            action="store_true",
            help="Explicitly approve applying the generated change.",
        )


def read_content_input(args: argparse.Namespace) -> str:
    """Read UTF-8 markdown content for note mutation commands."""
    return args.content_file.read_text(encoding="utf-8")

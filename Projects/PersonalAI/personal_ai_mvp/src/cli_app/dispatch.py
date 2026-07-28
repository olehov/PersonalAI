"""Dispatch helpers for the PersonalAI CLI entrypoint."""

from __future__ import annotations

import argparse

from cli_app.command_handlers import (
    handle_basic_command,
    handle_benchmark_command,
    handle_maintenance_command,
    handle_note_command,
    handle_training_command,
)


def dispatch_cli_command(args: argparse.Namespace, runtime, *, read_content_input) -> int | None:
    """Run the first matching CLI command handler."""
    for handler in (
        lambda: handle_basic_command(args, runtime),
        lambda: handle_benchmark_command(args, runtime),
        lambda: handle_note_command(args, runtime, read_content_input=read_content_input),
        lambda: handle_maintenance_command(args, runtime),
        lambda: handle_training_command(args, runtime),
    ):
        result = handler()
        if result is not None:
            return result
    return None


__all__ = [
    "dispatch_cli_command",
]

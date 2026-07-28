"""Backward-compatible facade for grouped CLI handlers."""

from cli_app.handlers import (
    handle_basic_command,
    handle_benchmark_command,
    handle_maintenance_command,
    handle_note_command,
    handle_training_command,
)

__all__ = [
    "handle_basic_command",
    "handle_benchmark_command",
    "handle_maintenance_command",
    "handle_note_command",
    "handle_training_command",
]

"""Grouped CLI command handlers."""

from cli_app.handlers.basic import handle_basic_command
from cli_app.handlers.benchmark import handle_benchmark_command
from cli_app.handlers.maintenance import handle_maintenance_command
from cli_app.handlers.notes import handle_note_command
from cli_app.handlers.training import handle_training_command

__all__ = [
    "handle_basic_command",
    "handle_benchmark_command",
    "handle_maintenance_command",
    "handle_note_command",
    "handle_training_command",
]

"""Grouped CLI subparser builders."""

from cli_app.parsers.basic import add_basic_parsers
from cli_app.parsers.benchmark import add_benchmark_parsers
from cli_app.parsers.maintenance import add_maintenance_parsers
from cli_app.parsers.notes import add_note_parsers
from cli_app.parsers.training import add_training_parsers

__all__ = [
    "add_basic_parsers",
    "add_benchmark_parsers",
    "add_maintenance_parsers",
    "add_note_parsers",
    "add_training_parsers",
]

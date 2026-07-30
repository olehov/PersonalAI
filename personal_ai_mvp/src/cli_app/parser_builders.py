"""Backward-compatible facade for grouped CLI subparser builders."""

from cli_app.parsers import (
    add_basic_parsers,
    add_benchmark_parsers,
    add_maintenance_parsers,
    add_note_parsers,
    add_training_parsers,
)

__all__ = [
    "add_basic_parsers",
    "add_benchmark_parsers",
    "add_maintenance_parsers",
    "add_note_parsers",
    "add_training_parsers",
]

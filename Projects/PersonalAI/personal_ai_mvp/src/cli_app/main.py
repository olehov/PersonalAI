"""Backward-compatible facade for the CLI entrypoint."""

from application.agent_runtime.service import AgentRuntimeService
from application.benchmark.run_service import BenchmarkRunService
from application.chat.service import ChatService
from application.notes.draft_service import NoteDraftService
from application.training.eval_service import TrainingEvalService
from application.training.fine_tune_service import TrainingFineTuneService
from cli_app.argument_helpers import (
    add_maintenance_draft_arguments,
    add_note_draft_arguments,
    add_note_mutation_arguments,
    default_history_db_path,
    read_content_input,
)
from cli_app.entry import build_parser, main
from cli_app.dispatch import dispatch_cli_command
from infrastructure.llm.ollama_client import OllamaClient
from infrastructure.config.settings import get_settings

__all__ = [
    "AgentRuntimeService",
    "BenchmarkRunService",
    "ChatService",
    "NoteDraftService",
    "OllamaClient",
    "TrainingEvalService",
    "TrainingFineTuneService",
    "add_maintenance_draft_arguments",
    "add_note_draft_arguments",
    "add_note_mutation_arguments",
    "build_parser",
    "default_history_db_path",
    "dispatch_cli_command",
    "get_settings",
    "main",
    "read_content_input",
]

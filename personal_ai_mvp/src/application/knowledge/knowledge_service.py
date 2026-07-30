"""Application service for loading and querying vault knowledge."""

from __future__ import annotations

from pathlib import Path

from application.knowledge.knowledge_index import KnowledgeIndex
from infrastructure.vault.reader import VaultReader


class KnowledgeService:
    """High-level application service for vault-backed note queries."""

    def __init__(self, vault_root: Path) -> None:
        self._vault_root = vault_root
        self._reader = VaultReader(vault_root)
        self._notes = []
        self._index = KnowledgeIndex()
        self._load_revision = 0

    def load(self) -> None:
        """Loads the vault into memory and rebuilds the note index."""
        self._notes = self._reader.read_all()
        self._index = KnowledgeIndex(self._notes)
        self._load_revision += 1

    def scan_summary(self) -> dict[str, int]:
        """Returns compact scan metrics for the currently loaded vault."""
        return {
            "note_count": len(self._notes),
            "notes_with_metadata": sum(1 for note in self._notes if note.metadata.values),
            "notes_with_links": sum(1 for note in self._notes if note.links),
        }

    def list_notes(self):
        """Lists all notes."""
        return self._index.list_notes()

    def search_notes(self, query: str):
        """Searches notes by title or content."""
        return self._index.search_notes(query)

    def get_related_notes(self, identifier: str | Path):
        """Gets related notes for a note title or path."""
        return self._index.get_related_notes(identifier)

    def get_note(self, identifier: str | Path):
        """Gets a single note by title or path."""
        return self._index.get_note(identifier)

    @property
    def vault_root(self) -> Path:
        """Returns the configured vault root."""
        return self._vault_root

    @property
    def load_revision(self) -> int:
        """Returns a monotonic revision incremented after each successful load."""
        return self._load_revision


# Backward-compatible re-exports for callers that still import serializers
# from application.knowledge_service.
from application.shared.serializers import (  # noqa: E402
    serialize_agent_run_history_entry,
    serialize_agent_runtime_artifact,
    serialize_applied_note_change,
    serialize_answer_bundle,
    serialize_benchmark_run_history_entry,
    serialize_directory_analysis_report,
    serialize_generated_answer,
    serialize_generated_note_draft,
    serialize_maintenance_draft_plan,
    serialize_maintenance_plan,
    serialize_maintenance_report,
    serialize_note,
    serialize_note_change_proposal,
    serialize_prompt_patch_plan,
    serialize_query_history_entry,
    serialize_retrieval_bundle,
    serialize_retrieved_note,
    serialize_training_corpus,
    serialize_training_evaluation_comparison,
    serialize_training_evaluation_leaderboard,
    serialize_training_evaluation_report,
    serialize_training_example,
    serialize_training_fine_tune_bundle,
    serialize_training_fine_tune_recipe,
    serialize_training_manifest,
    serialize_training_optimizer_leaderboard,
    serialize_training_optimizer_sweep_report,
    serialize_training_split,
    serialize_training_trainer_artifact,
)

from __future__ import annotations

from pathlib import Path
import unittest

from application.knowledge.answer_service import AnswerService
from application.knowledge.knowledge_service import KnowledgeService
from application.notes.draft_service import NoteDraftService
from application.notes.maintenance_service import KnowledgeMaintenanceService
from application.notes.mutation_service import NoteMutationService
from application.notes.policy import NotePolicy
from application.knowledge.retrieval_service import RetrievalService
from domain.models import PromptMessage


class FakeOllamaClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[PromptMessage, ...]]] = []

    def chat(self, model: str, messages: tuple[PromptMessage, ...]) -> str:
        self.calls.append((model, messages))
        return self.response


class NoteDraftServiceTestSupport(unittest.TestCase):
    def _build_draft_service(
        self,
        root: Path,
        *,
        response: str,
    ) -> tuple[KnowledgeService, NoteMutationService, FakeOllamaClient, NoteDraftService]:
        knowledge = KnowledgeService(root)
        knowledge.load()
        mutation = NoteMutationService(knowledge, NotePolicy(root))
        fake_client = FakeOllamaClient(response)
        draft_service = NoteDraftService(
            AnswerService(RetrievalService(knowledge)),
            mutation,
            fake_client,
        )
        return knowledge, mutation, fake_client, draft_service

    def _build_maintenance_draft_service(
        self,
        root: Path,
        *,
        response: str,
        finding_path: str,
        kind: str,
    ) -> tuple[object, FakeOllamaClient, NoteDraftService]:
        knowledge, mutation, fake_client, draft_service = self._build_draft_service(
            root,
            response=response,
        )
        maintenance = KnowledgeMaintenanceService(knowledge, mutation)
        finding = maintenance.find_finding(finding_path, kind=kind)
        self.assertIsNotNone(finding)
        return finding, fake_client, draft_service

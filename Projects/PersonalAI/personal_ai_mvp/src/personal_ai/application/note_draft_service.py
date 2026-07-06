"""Generate markdown note drafts and route them through the safe mutation pipeline."""

from __future__ import annotations

from personal_ai.application.answer_service import AnswerService
from personal_ai.application.note_draft_grounding import (
    build_grounding_tokens as _build_grounding_tokens,
    build_isolated_companion_proposals as _build_isolated_companion_proposals,
    build_note_lookup as _build_note_lookup,
    candidate_note_titles as _candidate_note_titles,
    enrich_isolated_note_links as _enrich_isolated_note_links,
    extract_preserved_facts as _extract_preserved_facts,
    stabilize_isolated_note_content as _stabilize_isolated_note_content,
)
from personal_ai.application.note_mutation_service import NoteMutationService
from personal_ai.application.note_draft_prompting import (
    build_draft_prompt,
    build_maintenance_prompt,
    derive_scope,
    refine_maintenance_answer_bundle,
    render_style_guide,
)
from personal_ai.application.note_draft_normalizer import (
    normalize_generated_note,
)
from personal_ai.domain.models import (
    GeneratedNoteDraft,
    KnowledgeMaintenanceFinding,
    KnowledgeMaintenancePlan,
    MaintenanceDraftPlan,
    MaintenanceDraftPlanEntry,
    NoteChangeAction,
    PromptMessage,
)
from personal_ai.infrastructure.ollama_client import OllamaClient


class NoteDraftService:
    """Creates grounded markdown drafts for note creation or updates."""

    SYSTEM_PROMPT = (
        "You write Obsidian markdown notes for a personal software engineering knowledge base. "
        "Return only the full markdown note content. "
        "Keep it structured, factual, and concise. "
        "Preserve useful existing information when updating a note. "
        "Do not include commentary outside the note body."
    )
    MAINTENANCE_PROMPT = (
        "You refactor existing Obsidian markdown notes for a personal software engineering knowledge base. "
        "Return only the full updated markdown note content. "
        "Preserve correct existing facts, improve structure, and strengthen internal links when grounded context supports it. "
        "Do not mention that this was generated from a maintenance task. "
        "Do not add self-referential maintenance commentary such as saying the note should be expanded, improved, or refactored."
    )

    def __init__(
        self,
        answer_service: AnswerService,
        mutation_service: NoteMutationService,
        ollama_client: OllamaClient,
    ) -> None:
        self._answer_service = answer_service
        self._mutation_service = mutation_service
        self._ollama_client = ollama_client

    def draft_note(
        self,
        *,
        title: str,
        instruction: str,
        model: str,
        action: NoteChangeAction | None = None,
        target_dir: str | None = None,
        target_path: str | None = None,
        scope_dirs: tuple[str, ...] = (),
    ) -> GeneratedNoteDraft:
        """Generates a markdown draft and wraps it in a safe proposal."""
        grounding_question = f"Prepare knowledge for note '{title}'. Instruction: {instruction}"
        derived_scope = scope_dirs or derive_scope(target_dir=target_dir, target_path=target_path)
        answer_bundle = self._answer_service.prepare_answer(
            grounding_question,
            scope_dirs=derived_scope,
        )
        prompt_messages = (
            PromptMessage(role="system", content=self.SYSTEM_PROMPT),
            PromptMessage(
                role="user",
                content=self._build_draft_prompt(
                    title=title,
                    instruction=instruction,
                    target_path=target_path,
                    answer_context=answer_bundle.messages[1].content,
                    style_guide=render_style_guide(
                        answer_bundle=answer_bundle,
                        authoritative_text="",
                    ),
                ),
            ),
        )
        content = normalize_generated_note(
            self._ollama_client.chat(model=model, messages=prompt_messages),
            note_lookup=_build_note_lookup(
                answer_bundle,
                self._mutation_service.build_note_lookup(),
            ),
            grounded_tokens=_build_grounding_tokens(answer_bundle, extra_texts=()),
        )
        proposal = self._mutation_service.propose_change(
            title=title,
            proposed_content=content,
            action=action,
            target_dir=target_dir,
            target_path=target_path,
        )
        return GeneratedNoteDraft(
            model=model,
            title=title,
            instruction=instruction,
            content=content,
            proposal=proposal,
            citations=answer_bundle.citations,
            prompt=answer_bundle,
        )

    def draft_maintenance_finding(
        self,
        *,
        finding: KnowledgeMaintenanceFinding,
        model: str,
    ) -> GeneratedNoteDraft:
        """Generates a grounded draft for a maintenance finding."""
        if finding.proposal is None:
            raise RuntimeError("This maintenance finding does not have an actionable proposal.")
        if finding.proposal.action != "refactor":
            raise RuntimeError("Only refactor maintenance findings can be drafted automatically.")

        scope_dirs = derive_scope(target_dir=None, target_path=finding.note.path.as_posix())
        grounding_question = (
            f"Improve note '{finding.note.title}' for maintenance. "
            f"Issue: {finding.summary}. Details: {'; '.join(finding.details)}"
        )
        answer_bundle = self._answer_service.prepare_answer(
            grounding_question,
            scope_dirs=scope_dirs,
        )
        answer_bundle = refine_maintenance_answer_bundle(answer_bundle, finding.note.path)
        prompt_messages = (
            PromptMessage(role="system", content=self.MAINTENANCE_PROMPT),
            PromptMessage(
                role="user",
                content=self._build_maintenance_prompt(
                    finding=finding,
                    answer_context=answer_bundle.messages[1].content,
                    citations=answer_bundle.citations,
                    related_titles=_candidate_note_titles(answer_bundle, exclude_title=finding.note.title),
                    style_guide=render_style_guide(
                        answer_bundle=answer_bundle,
                        authoritative_text=finding.note.content,
                    ),
                ),
            ),
        )
        content = normalize_generated_note(
            self._ollama_client.chat(model=model, messages=prompt_messages),
            note_lookup=_build_note_lookup(
                answer_bundle,
                self._mutation_service.build_note_lookup(),
            ),
            grounded_tokens=_build_grounding_tokens(
                answer_bundle,
                extra_texts=(finding.note.content,),
            ),
            authoritative_text=finding.note.content,
        )
        content = _stabilize_isolated_note_content(
            content,
            finding_kind=finding.kind,
            authoritative_text=finding.note.content,
        )
        content = _enrich_isolated_note_links(
            content,
            finding_kind=finding.kind,
            related_titles=_candidate_note_titles(answer_bundle, exclude_title=finding.note.title),
        )
        companion_proposals = _build_isolated_companion_proposals(
            finding=finding,
            answer_bundle=answer_bundle,
            mutation_service=self._mutation_service,
        )
        proposal = self._mutation_service.propose_change(
            title=finding.note.title,
            proposed_content=content,
            action=finding.proposal.action,
            target_path=finding.note.path.as_posix(),
        )
        return GeneratedNoteDraft(
            model=model,
            title=finding.note.title,
            instruction=f"Maintenance refactor: {finding.summary}",
            content=content,
            proposal=proposal,
            citations=answer_bundle.citations,
            companion_proposals=companion_proposals,
            prompt=answer_bundle,
        )

    def draft_maintenance_plan(
        self,
        *,
        plan: KnowledgeMaintenancePlan,
        model: str,
    ) -> MaintenanceDraftPlan:
        """Generates drafts for each entry in a maintenance plan."""
        entries: list[MaintenanceDraftPlanEntry] = []
        for plan_entry in plan.entries:
            draft = self.draft_maintenance_finding(
                finding=plan_entry.finding,
                model=model,
            )
            entries.append(
                MaintenanceDraftPlanEntry(
                    plan_entry=plan_entry,
                    draft=draft,
                )
            )
        return MaintenanceDraftPlan(entries=tuple(entries))

    def _build_draft_prompt(
        self,
        *,
        title: str,
        instruction: str,
        target_path: str | None,
        answer_context: str,
        style_guide: str,
    ) -> str:
        return build_draft_prompt(
            title=title,
            instruction=instruction,
            target_path=target_path,
            answer_context=answer_context,
            style_guide=style_guide,
        )

    def _build_maintenance_prompt(
        self,
        *,
        finding: KnowledgeMaintenanceFinding,
        answer_context: str,
        citations: tuple[str, ...],
        related_titles: tuple[str, ...],
        style_guide: str,
    ) -> str:
        return build_maintenance_prompt(
            finding=finding,
            answer_context=answer_context,
            citations=citations,
            related_titles=related_titles,
            style_guide=style_guide,
            preserved_facts=_extract_preserved_facts(finding.note.content),
        )

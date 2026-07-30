"""Retrieval logic for turning a question into a context bundle."""

from __future__ import annotations

import re
from pathlib import Path

from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_support.profile import (
    build_query_profile as _build_query_profile,
    matches_scope as _matches_scope,
    note_query_terms as _note_query_terms,
    note_selection_terms as _note_selection_terms,
    related_query_terms as _related_query_terms,
    term_overlap_ratio as _term_overlap_ratio,
    tokenize as _tokenize,
)
from application.knowledge.retrieval_support.scoring import (
    bridge_bonus as _bridge_bonus,
    entity_bonus as _entity_bonus,
    is_bridge_note as _is_bridge_note,
    meta_penalty as _meta_penalty,
    path_bonus as _path_bonus,
    score_note as _score_note,
    focus_bonus as _focus_bonus,
)
from application.knowledge.vector_index import InMemoryVectorIndex
from domain.models import NoteDocument, RetrievalBundle, RetrievedNote
from infrastructure.hashed_embedding_provider import HashedEmbeddingProvider


class RetrievalService:
    """Builds a small structured context bundle from a vault-backed knowledge service."""

    def __init__(self, knowledge_service: KnowledgeService, embedding_provider=None) -> None:
        self._knowledge_service = knowledge_service
        self._vector_index = InMemoryVectorIndex(
            embedding_provider if embedding_provider is not None else HashedEmbeddingProvider()
        )
        self._cached_index_key: tuple[int, tuple[str, ...]] | None = None

    def build_context(
        self,
        question: str,
        *,
        primary_limit: int = 3,
        related_limit: int = 5,
        scope_dirs: tuple[str, ...] = (),
        task_mode: str = "general",
    ) -> RetrievalBundle:
        """Ranks notes for a question and expands them with related notes."""
        tokens = _tokenize(question)
        notes = self._select_notes(scope_dirs)
        self._ensure_vector_index(notes, scope_dirs)
        semantic_scores = self._vector_index.search(question, top_k=max(primary_limit * 4, 8))
        profile = _build_query_profile(
            question,
            tokens,
            scope_dirs,
            task_mode=task_mode,
        )
        ranked_primary = self._rank_notes(tokens, notes, semantic_scores, profile)
        primary_notes = tuple(self._select_primary_notes(ranked_primary, tokens, primary_limit))

        related_notes = tuple(
            self._select_related_notes(
                primary_notes,
                question_tokens=tokens,
                semantic_scores=semantic_scores,
                profile=profile,
                related_limit=related_limit,
            )
        )

        return RetrievalBundle(
            question=question,
            primary_notes=primary_notes,
            related_notes=related_notes,
        )

    def _select_primary_notes(
        self,
        ranked: list[RetrievedNote],
        question_tokens: set[str],
        limit: int,
    ) -> list[RetrievedNote]:
        if limit <= 0 or not ranked:
            return []

        selected: list[RetrievedNote] = []
        covered_tokens: set[str] = set()
        remaining = list(ranked)

        while remaining and len(selected) < limit:
            best_index = max(
                range(len(remaining)),
                key=lambda index: self._primary_selection_score(
                    remaining[index],
                    selected,
                    covered_tokens,
                    question_tokens,
                ),
            )
            chosen = remaining.pop(best_index)
            selected.append(chosen)
            covered_tokens.update(_note_query_terms(chosen.note, question_tokens))

        return selected

    def _rank_notes(
        self,
        tokens: set[str],
        notes: list[NoteDocument],
        semantic_scores: dict[Path, float],
        profile: dict[str, object],
    ) -> list[RetrievedNote]:
        ranked: list[RetrievedNote] = []
        for note in notes:
            score, reason, debug_signals = _score_note(
                tokens,
                note,
                profile,
                semantic_score=semantic_scores.get(note.path, 0.0),
            )
            if score > 0:
                ranked.append(
                    RetrievedNote(
                        note=note,
                        score=score,
                        reason=reason,
                        debug_signals=debug_signals,
                    )
                )

        ranked = self._apply_graph_reranking(ranked, profile)
        return sorted(ranked, key=lambda item: (-item.score, item.note.path.as_posix()))

    def _select_related_notes(
        self,
        primary_notes: tuple[RetrievedNote, ...],
        *,
        question_tokens: set[str],
        semantic_scores: dict[Path, float],
        profile: dict[str, object],
        related_limit: int,
    ) -> list[RetrievedNote]:
        if related_limit <= 0 or not primary_notes:
            return []

        seen_paths = {item.note.path for item in primary_notes}
        related_candidates: dict[Path, RetrievedNote] = {}

        for item in primary_notes:
            for related in self._knowledge_service.get_related_notes(item.note.path):
                if related.path in seen_paths:
                    continue

                existing = related_candidates.get(related.path)
                base_score = max(item.score - 1, 1)
                candidate = existing or RetrievedNote(
                    note=related,
                    score=base_score,
                    reason=f"linked from {item.note.title}",
                    debug_signals={
                        "origin": "related_candidate",
                        "linked_from": [item.note.title],
                        "base_score": base_score,
                    },
                )
                if existing is not None:
                    candidate = RetrievedNote(
                        note=related,
                        score=existing.score + 2,
                        reason=f"{existing.reason}; linked from {item.note.title}",
                        debug_signals={
                            **existing.debug_signals,
                            "linked_from": [
                                *list(existing.debug_signals.get("linked_from", [])),
                                item.note.title,
                            ],
                            "base_score": existing.score + 2,
                        },
                    )

                adjusted = self._adjust_related_candidate(
                    candidate,
                    question_tokens=question_tokens,
                    semantic_score=semantic_scores.get(related.path, 0.0),
                    profile=profile,
                )
                if adjusted is not None:
                    related_candidates[related.path] = adjusted

        return sorted(
            related_candidates.values(),
            key=lambda item: (-item.score, item.note.path.as_posix()),
        )[:related_limit]

    def _select_notes(self, scope_dirs: tuple[str, ...]) -> list[NoteDocument]:
        notes = self._knowledge_service.list_notes()
        normalized_scopes = tuple(scope.casefold() for scope in scope_dirs if scope.strip())
        if not normalized_scopes:
            return notes

        scoped_notes = [
            note
            for note in notes
            if _matches_scope(note.path, normalized_scopes)
        ]
        return scoped_notes or notes

    def _ensure_vector_index(
        self,
        notes: list[NoteDocument],
        scope_dirs: tuple[str, ...],
    ) -> None:
        normalized_scopes = tuple(scope.casefold() for scope in scope_dirs if scope.strip())
        effective_scopes = normalized_scopes if normalized_scopes else ("__all__",)
        cache_key = (self._knowledge_service.load_revision, effective_scopes)
        if self._cached_index_key == cache_key:
            return
        self._vector_index.rebuild(notes)
        self._cached_index_key = cache_key

    def _apply_graph_reranking(
        self,
        ranked: list[RetrievedNote],
        profile: dict[str, object],
    ) -> list[RetrievedNote]:
        if not ranked:
            return ranked

        candidate_scores = {item.note.path: item.score for item in ranked}
        reranked: list[RetrievedNote] = []
        for item in ranked:
            bonus = self._graph_bonus(item.note, candidate_scores, profile)
            if bonus <= 0:
                reranked.append(item)
                continue

            reranked.append(
                RetrievedNote(
                    note=item.note,
                    score=item.score + bonus,
                    reason=f"{item.reason}, graph link bonus",
                    debug_signals={
                        **item.debug_signals,
                        "graph": {
                            "bonus": bonus,
                            "related_candidate_count": len(
                                self._knowledge_service.get_related_notes(item.note.path)
                            ),
                        },
                        "final_score": item.score + bonus,
                    },
                )
            )

        return reranked

    def _graph_bonus(
        self,
        note: NoteDocument,
        candidate_scores: dict[Path, int],
        profile: dict[str, object],
    ) -> int:
        related = self._knowledge_service.get_related_notes(note.path)
        if not related:
            return 0

        bonus = 0
        strong_neighbor_count = 0
        for related_note in related:
            related_score = candidate_scores.get(related_note.path)
            if not related_score:
                continue

            strong_neighbor_count += 1
            bonus += 1
            if related_score >= 18:
                bonus += 1
            if profile["cross_domain"] and _is_bridge_note(related_note.path):
                bonus += 1

        if strong_neighbor_count >= 2:
            bonus += 1

        return bonus

    def _primary_selection_score(
        self,
        candidate: RetrievedNote,
        selected: list[RetrievedNote],
        covered_tokens: set[str],
        question_tokens: set[str],
    ) -> tuple[int, int, str]:
        if not selected:
            return (candidate.score, candidate.score, candidate.note.path.as_posix())

        candidate_terms = _note_selection_terms(candidate.note)
        query_terms = candidate_terms & question_tokens
        uncovered_terms = query_terms - covered_tokens
        redundancy = max(
            _term_overlap_ratio(candidate_terms, _note_selection_terms(item.note))
            for item in selected
        )

        diversity_bonus = len(uncovered_terms) * 3
        relation_bonus = 2 if self._shares_link_with_selected(candidate.note, selected) else 0
        redundancy_penalty = int(round(redundancy * 10))
        adjusted_score = candidate.score + diversity_bonus + relation_bonus - redundancy_penalty

        return (adjusted_score, candidate.score, candidate.note.path.as_posix())

    def _shares_link_with_selected(
        self,
        candidate: NoteDocument,
        selected: list[RetrievedNote],
    ) -> bool:
        candidate_related = {note.path for note in self._knowledge_service.get_related_notes(candidate.path)}
        if not candidate_related:
            return False

        selected_paths = {item.note.path for item in selected}
        return bool(candidate_related & selected_paths)

    def _adjust_related_candidate(
        self,
        candidate: RetrievedNote,
        *,
        question_tokens: set[str],
        semantic_score: float,
        profile: dict[str, object],
    ) -> RetrievedNote | None:
        note = candidate.note
        candidate_terms = _note_selection_terms(note)
        query_overlap = len(_related_query_terms(note) & question_tokens)
        semantic_points = int(round(semantic_score * 10))
        path_bonus = _path_bonus(note.path, profile, [])
        bridge_bonus = _bridge_bonus(note.path, profile, [])
        bridge_penalty = 0
        if _is_bridge_note(note.path) and not profile["cross_domain"] and query_overlap == 0:
            bridge_penalty = 8
        meta_penalty = 0
        if profile["focused_coding"]:
            lower_parts = [part.casefold() for part in note.path.parts]
            if lower_parts[-1] in {
                "project index.md",
                "readme.md",
                "roadmap.md",
                "vision.md",
                "technology stack.md",
                "mvp.md",
            }:
                meta_penalty = 10

        adjusted_score = (
            candidate.score
            + query_overlap
            + semantic_points
            + path_bonus
            + bridge_bonus
            - bridge_penalty
            - meta_penalty
        )
        if not profile["technical"] and query_overlap == 0 and semantic_points <= 0 and path_bonus <= 0:
            return candidate

        if (
            _is_bridge_note(note.path)
            and not profile["cross_domain"]
            and path_bonus <= 0
            and query_overlap < 3
            and semantic_points < 4
        ):
            return None
        if (
            profile["focused_coding"]
            and meta_penalty > 0
            and query_overlap < 3
            and semantic_points < 6
        ):
            return None

        if query_overlap == 0 and semantic_points <= 0 and path_bonus <= 0 and bridge_bonus <= 0:
            return None
        if adjusted_score <= 0:
            return None

        reasons = [candidate.reason]
        if query_overlap:
            reasons.append("question overlap")
        if semantic_points > 0:
            reasons.append(f"semantic support {semantic_score:.2f}")
        if path_bonus > 0:
            matched_dirs = sorted(profile["preferred_dirs"] & {part.casefold() for part in note.path.parts[:-1]})
            reasons.append(f"directory preference: {', '.join(matched_dirs)}")
        if bridge_bonus > 0:
            reasons.append("bridge note bonus")
        if bridge_penalty > 0:
            reasons.append("bridge note penalty")
        if meta_penalty > 0:
            reasons.append("meta note penalty")

        return RetrievedNote(
            note=note,
            score=adjusted_score,
            reason=", ".join(reasons),
            debug_signals={
                **candidate.debug_signals,
                "related_adjustment": {
                    "query_overlap": query_overlap,
                    "semantic_score": semantic_score,
                    "semantic_points": semantic_points,
                    "path_bonus": path_bonus,
                    "bridge_bonus": bridge_bonus,
                    "bridge_penalty": bridge_penalty,
                    "meta_penalty": meta_penalty,
                },
                "reason_tags": reasons,
                "final_score": adjusted_score,
            },
        )

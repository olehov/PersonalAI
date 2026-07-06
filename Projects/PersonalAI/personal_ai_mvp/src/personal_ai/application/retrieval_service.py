"""Retrieval logic for turning a question into a context bundle."""

from __future__ import annotations

import re
from pathlib import Path

from personal_ai.application.knowledge_service import KnowledgeService
from personal_ai.application.vector_index import InMemoryVectorIndex
from personal_ai.domain.models import NoteDocument, RetrievalBundle, RetrievedNote
from personal_ai.infrastructure.hashed_embedding_provider import HashedEmbeddingProvider


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "while",
    "why",
    "with",
}

BRIDGE_TITLES = {
    "observability.md",
    "caching.md",
    "retries and timeouts.md",
    "queues and backpressure.md",
}

BRIDGE_DIRS = {
    "architecture decisions",
    "optimizations",
    "bugs",
    "design patterns",
}


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
    ) -> RetrievalBundle:
        """Ranks notes for a question and expands them with related notes."""
        tokens = _tokenize(question)
        notes = self._select_notes(scope_dirs)
        self._ensure_vector_index(notes, scope_dirs)
        semantic_scores = self._vector_index.search(question, top_k=max(primary_limit * 4, 8))
        profile = _build_query_profile(question, tokens, scope_dirs)
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
            score, reason = _score_note(
                tokens,
                note,
                profile,
                semantic_score=semantic_scores.get(note.path, 0.0),
            )
            if score > 0:
                ranked.append(RetrievedNote(note=note, score=score, reason=reason))

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
                )
                if existing is not None:
                    candidate = RetrievedNote(
                        note=related,
                        score=existing.score + 2,
                        reason=f"{existing.reason}; linked from {item.note.title}",
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

        adjusted_score = candidate.score + query_overlap + semantic_points + path_bonus + bridge_bonus - bridge_penalty
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

        return RetrievedNote(
            note=note,
            score=adjusted_score,
            reason=", ".join(reasons),
        )


def _score_note(
    tokens: set[str],
    note: NoteDocument,
    profile: dict[str, object],
    *,
    semantic_score: float,
) -> tuple[int, str]:
    if not tokens:
        return 0, "no query terms"

    title_terms = _tokenize(note.title)
    content_terms = _tokenize(note.content)
    path_terms = _tokenize(note.path.as_posix())

    title_matches = len(tokens & title_terms)
    content_matches = len(tokens & content_terms)
    path_matches = len(tokens & path_terms)
    score = title_matches * 4 + content_matches + path_matches * 2
    reasons: list[str] = []

    if title_matches:
        reasons.append("title match")
    if content_matches:
        reasons.append("content match")
    if path_matches:
        reasons.append("path match")

    semantic_points = int(round(semantic_score * 10))
    if semantic_points > 0:
        score += semantic_points
        reasons.append(f"semantic match {semantic_score:.2f}")

    score += _focus_bonus(tokens, note, profile, reasons)
    score += _bridge_bonus(note.path, profile, reasons)
    score += _path_bonus(note.path, profile, reasons)
    score -= _meta_penalty(note.path, profile, reasons)

    if score > 0 and reasons:
        return score, ", ".join(reasons)
    return 0, "no match"


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_]{2,}", text.casefold())
        if token not in STOPWORDS
    }


def _build_query_profile(question: str, tokens: set[str], scope_dirs: tuple[str, ...]) -> dict[str, object]:
    normalized = question.casefold()
    preferred_dirs: set[str] = set()
    technical = False

    topic_map = {
        "Algorithms": {"algorithm", "algorithms", "heap", "binary", "search", "graph", "tree", "dp"},
        "Linux": {"linux", "kernel", "bash", "shell", "systemd", "ubuntu", "debian"},
        "Networking": {"network", "networking", "tcp", "udp", "http", "dns", "socket"},
        "Languages": {"python", "javascript", "java", "cpp", "cxx", "c++"},
        "Design Patterns": {"pattern", "patterns", "factory", "strategy", "observer"},
        "Optimizations": {"optimization", "performance", "latency", "throughput"},
        "Bugs": {"bug", "bugs", "error", "crash", "fix", "incident"},
    }

    for directory, keywords in topic_map.items():
        if tokens & keywords:
            preferred_dirs.add(directory.casefold())
            technical = True

    if {"implementation", "complexity", "operations", "datastructure", "data", "structure"} & tokens:
        technical = True
        preferred_dirs.add("algorithms")

    if "code" in tokens or "engineering" in tokens:
        technical = True

    preferred_dirs.update(scope.casefold() for scope in scope_dirs if scope.strip())
    if preferred_dirs:
        technical = True

    bridge_keywords = {
        "observability",
        "debugging",
        "distributed",
        "resilience",
        "retries",
        "timeouts",
        "backpressure",
        "caching",
        "latency",
        "throughput",
        "reliability",
        "availability",
    }
    cross_domain = len(preferred_dirs) >= 2 or bool(tokens & bridge_keywords)

    return {
        "normalized_question": normalized,
        "preferred_dirs": preferred_dirs,
        "technical": technical,
        "cross_domain": cross_domain,
    }


def _path_bonus(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    preferred_dirs = profile["preferred_dirs"]
    path_parts = {part.casefold() for part in path.parts[:-1]}
    matched_dirs = sorted(preferred_dirs & path_parts)
    if not matched_dirs:
        return 0

    reasons.append(f"directory preference: {', '.join(matched_dirs)}")
    return 6 * len(matched_dirs)


def _focus_bonus(
    tokens: set[str],
    note: NoteDocument,
    profile: dict[str, object],
    reasons: list[str],
) -> int:
    title_terms = _tokenize(note.title)
    if not title_terms:
        return 0

    matched_terms = tokens & title_terms
    if not matched_terms:
        return 0

    if matched_terms == title_terms:
        bonus = 2
        if profile["cross_domain"] and _is_bridge_note(note.path):
            bonus += 4
        reasons.append("focus match")
        return bonus

    return 0


def _meta_penalty(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    if not profile["technical"]:
        return 0

    if _is_bridge_note(path) and profile["cross_domain"]:
        return 0

    meta_parts = {
        "architecture decisions",
        "projects",
    }
    meta_names = {
        "readme.md",
        "mvp.md",
        "roadmap.md",
        "vision.md",
        "technology stack.md",
    }

    penalty = 0
    lower_parts = [part.casefold() for part in path.parts]
    if any(part in meta_parts for part in lower_parts[:-1]):
        penalty += 3
    if lower_parts[-1] in meta_names:
        penalty += 4
    if "personal_ai_mvp" in lower_parts:
        penalty += 6

    if penalty:
        reasons.append("meta note penalty")
    return penalty


def _bridge_bonus(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    if not profile["cross_domain"]:
        return 0

    lower_parts = [part.casefold() for part in path.parts]
    bonus = 0
    if lower_parts[-1] in BRIDGE_TITLES:
        bonus += 8
    if any(part in BRIDGE_DIRS for part in lower_parts[:-1]):
        bonus += 4

    if bonus:
        reasons.append("bridge note bonus")
    return bonus


def _is_bridge_note(path: Path) -> bool:
    lower_parts = [part.casefold() for part in path.parts]
    return lower_parts[-1] in BRIDGE_TITLES or any(
        part in BRIDGE_DIRS for part in lower_parts[:-1]
    )


def _matches_scope(path: Path, normalized_scopes: tuple[str, ...]) -> bool:
    lower_parts = [part.casefold() for part in path.parts]
    return any(scope in lower_parts for scope in normalized_scopes)


def _note_query_terms(note: NoteDocument, question_tokens: set[str]) -> set[str]:
    return _note_selection_terms(note) & question_tokens


def _note_selection_terms(note: NoteDocument) -> set[str]:
    return _tokenize(" ".join((note.title, note.path.as_posix(), note.content)))


def _related_query_terms(note: NoteDocument) -> set[str]:
    content = re.sub(r"\[\[[^\]]+\]\]", " ", note.content)
    return _tokenize(" ".join((note.title, note.path.as_posix(), content)))


def _term_overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0

    union = left | right
    if not union:
        return 0.0

    return len(left & right) / len(union)

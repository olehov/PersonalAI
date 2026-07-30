"""Scoring helpers for retrieval note ranking."""

from __future__ import annotations

from pathlib import Path

from application.knowledge.retrieval_support.classification import (
    is_bridge_note,
    note_class_name,
    note_class_bonus,
)
from application.knowledge.retrieval_support.profile import tokenize
from domain.models import NoteDocument


def score_note(
    tokens: set[str],
    note: NoteDocument,
    profile: dict[str, object],
    *,
    semantic_score: float,
) -> tuple[int, str, dict[str, object]]:
    if not tokens:
        return 0, "no query terms", {"note_class": note_class_name(note.path)}

    title_terms = tokenize(note.title)
    content_terms = tokenize(note.content)
    path_terms = tokenize(note.path.as_posix())
    note_class = note_class_name(note.path)

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

    focus_points = focus_bonus(tokens, note, profile, reasons)
    entity_points = entity_bonus(note, profile, reasons)
    note_class_points = note_class_bonus(note.path, profile, reasons)
    bridge_points = bridge_bonus(note.path, profile, reasons)
    path_points = path_bonus(note.path, profile, reasons)
    meta_points = meta_penalty(note.path, profile, reasons)
    self_project_points = self_project_penalty(note.path, profile, reasons)

    score += focus_points
    score += entity_points
    score += note_class_points
    score += bridge_points
    score += path_points
    score -= meta_points
    score -= self_project_points

    debug_signals = {
        "note_class": note_class,
        "match_counts": {
            "title": title_matches,
            "content": content_matches,
            "path": path_matches,
        },
        "semantic": {
            "score": semantic_score,
            "points": semantic_points,
        },
        "bonuses": {
            "focus": focus_points,
            "entity": entity_points,
            "note_class": note_class_points,
            "bridge": bridge_points,
            "path": path_points,
        },
        "penalties": {
            "meta": meta_points,
            "self_project": self_project_points,
        },
        "profile": {
            "task_mode": profile["task_mode"],
            "focused_coding": profile["focused_coding"],
            "cross_domain": profile["cross_domain"],
            "strict_meta_filtering": profile["strict_meta_filtering"],
            "preferred_dirs": sorted(profile["preferred_dirs"]),
        },
        "reason_tags": list(reasons),
        "final_score": score,
    }

    if score > 0 and reasons:
        return score, ", ".join(reasons), debug_signals
    return 0, "no match", debug_signals


def path_bonus(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    preferred_dirs = profile["preferred_dirs"]
    path_parts = {part.casefold() for part in path.parts[:-1]}
    matched_dirs = sorted(preferred_dirs & path_parts)
    if not matched_dirs:
        return 0

    reasons.append(f"directory preference: {', '.join(matched_dirs)}")
    return 6 * len(matched_dirs)


def focus_bonus(
    tokens: set[str],
    note: NoteDocument,
    profile: dict[str, object],
    reasons: list[str],
) -> int:
    title_terms = tokenize(note.title)
    if not title_terms:
        return 0

    matched_terms = tokens & title_terms
    if not matched_terms:
        return 0

    if matched_terms == title_terms:
        bonus = 2
        if profile["cross_domain"] and is_bridge_note(note.path):
            bonus += 4
        reasons.append("focus match")
        return bonus

    return 0


def entity_bonus(
    note: NoteDocument,
    profile: dict[str, object],
    reasons: list[str],
) -> int:
    if not profile["focused_coding"]:
        return 0

    focus_entities: set[str] = profile["focus_entities"]
    if not focus_entities:
        return 0

    note_terms = tokenize(" ".join((note.title, note.path.as_posix())))
    matched_entities = sorted(focus_entities & note_terms)
    if not matched_entities:
        return 0

    reasons.append(f"entity match: {', '.join(matched_entities)}")
    return 5 + len(matched_entities) * 4


def meta_penalty(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    if not profile["technical"]:
        return 0

    task_mode = str(profile["task_mode"])

    if is_bridge_note(path) and profile["cross_domain"]:
        return 0

    meta_parts = {
        "architecture decisions",
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
    if profile["focused_coding"]:
        if any(part in {"architecture decisions"} for part in lower_parts[:-1]):
            penalty += 3
        if lower_parts[-1] in {
            "project index.md",
            "readme.md",
            "roadmap.md",
            "vision.md",
            "technology stack.md",
            "mvp.md",
        }:
            penalty += 8
    if task_mode == "coding":
        if lower_parts[-1] in {
            "project index.md",
            "readme.md",
            "roadmap.md",
            "vision.md",
            "technology stack.md",
            "mvp.md",
        }:
            penalty += 6
    if task_mode == "agent":
        if lower_parts[-1] in {
            "project index.md",
            "readme.md",
            "roadmap.md",
            "vision.md",
            "technology stack.md",
            "mvp.md",
        }:
            penalty += 4
    if task_mode == "note_draft":
        if lower_parts[-1] in {
            "project index.md",
            "readme.md",
            "roadmap.md",
            "vision.md",
            "technology stack.md",
            "mvp.md",
        }:
            penalty += 10
    if profile["strict_meta_filtering"]:
        if lower_parts[-1] in {
            "project index.md",
            "readme.md",
            "roadmap.md",
            "vision.md",
            "technology stack.md",
            "mvp.md",
        }:
            if any(part in {"projects", "architecture decisions"} for part in lower_parts[:-1]):
                penalty += 6
            penalty += 14

    if penalty:
        reasons.append("meta note penalty")
    return penalty


def self_project_penalty(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    lower_parts = [part.casefold() for part in path.parts]
    if len(lower_parts) < 3:
        return 0
    if lower_parts[0] != "projects" or lower_parts[1] != "personalai":
        return 0
    if profile["references_personal_ai_project"]:
        return 0
    if not profile["technical"]:
        return 0

    penalty = 16
    if profile["task_mode"] == "implementation":
        penalty += 20
    elif profile["task_mode"] == "coding":
        penalty += 10
    elif profile["task_mode"] == "agent":
        penalty += 8
    elif profile["task_mode"] == "note_draft":
        penalty += 6
    if profile["focused_coding"]:
        penalty += 10

    reasons.append("self project penalty")
    return penalty


def bridge_bonus(path: Path, profile: dict[str, object], reasons: list[str]) -> int:
    if not profile["cross_domain"]:
        return 0

    lower_parts = [part.casefold() for part in path.parts]
    bonus = 0
    if is_bridge_note(path) and lower_parts[-1] in {
        "observability.md",
        "caching.md",
        "retries and timeouts.md",
        "queues and backpressure.md",
    }:
        bonus += 8
    if any(
        part in {"architecture decisions", "optimizations", "bugs", "design patterns"}
        for part in lower_parts[:-1]
    ):
        bonus += 4

    if bonus:
        reasons.append("bridge note bonus")
    return bonus

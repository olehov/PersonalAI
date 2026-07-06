"""Scoring and failure-analysis helpers for training evaluation."""

from __future__ import annotations

import re
from collections import Counter

from personal_ai.domain.models import (
    PromptPatchSuggestion,
    TrainingEvaluationExampleResult,
    TrainingEvaluationFailureSnapshot,
)


def score_output(output_markdown: str, target_markdown: str) -> float:
    """Compute a compact similarity score between output and target markdown."""
    exact_bonus = 1.0 if output_markdown == target_markdown else 0.0
    token_score = overlap_ratio(tokens(output_markdown), tokens(target_markdown))
    heading_score = overlap_ratio(headings(output_markdown), headings(target_markdown))
    link_score = overlap_ratio(links(output_markdown), links(target_markdown))
    return round(
        (exact_bonus * 0.4) + (token_score * 0.3) + (heading_score * 0.15) + (link_score * 0.15),
        4,
    )


def tokens(text: str) -> set[str]:
    """Extract normalized scoring tokens from markdown text."""
    return set(re.findall(r"[A-Za-z0-9_]{3,}", text.casefold()))


def headings(text: str) -> set[str]:
    """Extract normalized markdown headings."""
    return {
        line.strip().casefold()
        for line in text.splitlines()
        if line.strip().startswith("#")
    }


def links(text: str) -> set[str]:
    """Extract Obsidian link targets."""
    return set(re.findall(r"\[\[([^\]]+)\]\]", text))


def link_count(text: str) -> int:
    """Count Obsidian links in markdown text."""
    return len(links(text))


def heading_count(text: str) -> int:
    """Count markdown headings in markdown text."""
    return len(headings(text))


def overlap_ratio(left: set[str], right: set[str]) -> float:
    """Compute Jaccard-style overlap for scoring fragments."""
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def build_failure_snapshots(
    results: tuple[TrainingEvaluationExampleResult, ...],
    *,
    limit: int,
) -> tuple[TrainingEvaluationFailureSnapshot, ...]:
    """Build the weakest example snapshots for review and prompt patching."""
    weakest_results = sorted(
        results,
        key=lambda item: (item.score, item.exact_match, item.example_id),
    )[:limit]
    return tuple(
        TrainingEvaluationFailureSnapshot(
            example_id=result.example_id,
            source_note_path=result.source_note_path,
            task=result.task,
            score=result.score,
            exact_match=result.exact_match,
            output_markdown_preview=preview_text(result.output_markdown),
            error_tags=classify_failure_tags(result),
        )
        for result in weakest_results
    )


def preview_text(text: str, *, limit: int = 220) -> str:
    """Collapse and truncate markdown for lightweight failure previews."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def classify_failure_tags(
    result: TrainingEvaluationExampleResult,
) -> tuple[str, ...]:
    """Classify the dominant failure tags for one evaluated example."""
    tags: list[str] = []
    lower_output = result.output_markdown.casefold()

    if lower_output.startswith("here is") or "rewritten note" in lower_output:
        tags.append("meta_preface")
    if result.output_heading_count < result.target_heading_count:
        tags.append("missing_headings")
    if result.output_link_count < result.target_link_count:
        tags.append("missing_links")
    elif result.output_link_count > result.target_link_count:
        tags.append("link_drift")
    if "**" in result.output_markdown or "vault house style" in lower_output:
        tags.append("style_drift")

    if not tags and not result.exact_match:
        tags.append("content_drift")

    return tuple(tags)


def build_prompt_patch_suggestions(
    failure_snapshots: tuple[TrainingEvaluationFailureSnapshot, ...],
) -> tuple[PromptPatchSuggestion, ...]:
    """Convert repeated failure tags into prompt patch suggestions."""
    tag_counts: Counter[str] = Counter(
        tag
        for snapshot in failure_snapshots
        for tag in snapshot.error_tags
    )
    suggestions: list[PromptPatchSuggestion] = []
    for tag, occurrences in tag_counts.most_common():
        instruction, rationale = prompt_patch_for_tag(tag)
        suggestions.append(
            PromptPatchSuggestion(
                error_tag=tag,
                occurrences=occurrences,
                instruction=instruction,
                rationale=rationale,
            )
        )
    return tuple(suggestions)


def prompt_patch_for_tag(tag: str) -> tuple[str, str]:
    """Map one failure tag to a prompt-patch instruction and rationale."""
    mapping = {
        "meta_preface": (
            "Start directly with note content. Do not add prefatory phrases like 'Here is the rewritten note'.",
            "The model is adding assistant-style framing instead of pure vault markdown.",
        ),
        "missing_headings": (
            "Preserve the same heading hierarchy as the target note when headings already exist.",
            "The model is collapsing or omitting expected markdown sections.",
        ),
        "missing_links": (
            "Keep all grounded internal [[Note Title]] links that appear in the source target style.",
            "The model is dropping relevant graph connections from the rewritten note.",
        ),
        "link_drift": (
            "Do not invent extra internal links beyond grounded related notes already supported by context.",
            "The model is adding link noise or unsupported graph edges.",
        ),
        "style_drift": (
            "Use plain Obsidian markdown house style: compact headings and bullets, no decorative emphasis or style commentary.",
            "The model is drifting into flashy formatting or explaining the style inside the note.",
        ),
        "content_drift": (
            "Stay close to grounded facts and compact note structure; avoid speculative rewrites.",
            "The output diverges from target content without a single dominant formatting error.",
        ),
    }
    return mapping.get(
        tag,
        (
            "Preserve grounded facts and the existing note template more strictly.",
            "A recurring rewrite issue needs stronger structure-preservation guidance.",
        ),
    )


def model_profile_suggestions(model: str) -> tuple[PromptPatchSuggestion, ...]:
    """Provide model-family-specific prompt hints to reduce known drift patterns."""
    lowered = model.casefold()
    if "qwen" in lowered:
        return (
            PromptPatchSuggestion(
                error_tag="model_profile_qwen_links",
                occurrences=0,
                instruction="Use internal links strictly as [[Note Title]] and never emit markdown links like [Title](...).",
                rationale="Qwen-family models often substitute markdown links for Obsidian links.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_qwen_link_lines",
                occurrences=0,
                instruction="When listing related notes, emit each related note exactly as a standalone [[Note Title]] entry instead of plain text labels.",
                rationale="Qwen-family models often keeps note names as plain text instead of preserving Obsidian link syntax.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_qwen_plain_bullets",
                occurrences=0,
                instruction="Keep bullets plain and compact; do not turn note sections into polished explanatory prose.",
                rationale="Qwen-family models tend to over-polish concise vault notes.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_qwen_no_alias_drift",
                occurrences=0,
                instruction="Do not rename canonical related-note titles; preserve the exact note title inside each [[...]] link.",
                rationale="Qwen-family models can paraphrase note titles and weaken exact vault link matching.",
            ),
        )
    if "mistral" in lowered:
        return (
            PromptPatchSuggestion(
                error_tag="model_profile_mistral_no_fences",
                occurrences=0,
                instruction="Do not wrap the note in code fences and do not prefix it with labels like Title:.",
                rationale="Mistral-family models often emit presentation wrappers instead of raw note content.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_mistral_headings",
                occurrences=0,
                instruction="Render section structure with markdown headings, not prose labels or list prefixes.",
                rationale="Mistral-family models tend to collapse headings into titled bullet lists.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_mistral_links",
                occurrences=0,
                instruction="Use only raw Obsidian [[Note Title]] links and never file-path markdown links.",
                rationale="Mistral-family models often drift toward path-style links.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_mistral_keep_bullets",
                occurrences=0,
                instruction="Preserve the original bullet count and section granularity; do not collapse several factual bullets into a single summarized sentence.",
                rationale="Mistral-family models often compress compact note bullets into broader summaries.",
            ),
            PromptPatchSuggestion(
                error_tag="model_profile_mistral_low_paraphrase",
                occurrences=0,
                instruction="Stay close to the source phrasing for factual bullets and cross-domain connections; prefer light normalization over creative paraphrasing.",
                rationale="Mistral-family models tend to rewrite grounded content too aggressively on cross-cluster notes.",
            ),
        )
    if "llama3" in lowered or "llama" in lowered:
        return (
            PromptPatchSuggestion(
                error_tag="model_profile_llama_no_preface",
                occurrences=0,
                instruction="Never preface the answer with phrases like 'Here is the rewritten note'; begin immediately with note content.",
                rationale="Llama-family models often add assistant framing before the note.",
            ),
        )
    return ()


def dedupe_preserve_order(items: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate a sequence while preserving the original order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return tuple(ordered)

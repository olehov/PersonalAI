"""CLI renderers for training corpora, eval, and optimizer workflows."""

from __future__ import annotations

import json

from application.shared.serializers import (
    serialize_prompt_patch_plan,
    serialize_training_corpus,
    serialize_training_evaluation_comparison,
    serialize_training_evaluation_leaderboard,
    serialize_training_evaluation_report,
    serialize_training_fine_tune_bundle,
    serialize_training_manifest,
    serialize_training_optimizer_leaderboard,
    serialize_training_optimizer_sweep_report,
    serialize_training_split,
)
from cli_app.rendering.training_support import (
    render_prompt_patch_plan_text,
    render_training_corpus_jsonl,
    render_training_corpus_text,
    render_training_evaluation_comparison_text,
    render_training_evaluation_leaderboard_text,
    render_training_evaluation_report_text,
    render_training_fine_tune_bundle_text,
    render_training_manifest_text,
    render_training_optimizer_leaderboard_text,
    render_training_optimizer_sweep_report_text,
    render_training_split_text,
    select_split_examples,
)


def render_training_corpus(corpus, output_format: str, dataset_format: str) -> str:
    payload = serialize_training_corpus(corpus)
    if dataset_format == "jsonl_chat":
        return render_training_corpus_jsonl(payload["examples"], mode="chat")
    if dataset_format == "jsonl_completion":
        return render_training_corpus_jsonl(payload["examples"], mode="completion")
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_corpus_text(payload)


def render_training_manifest(manifest, output_format: str) -> str:
    payload = serialize_training_manifest(manifest)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_manifest_text(payload)


def render_training_split(split, output_format: str, dataset_format: str, subset: str) -> str:
    payload = serialize_training_split(split)
    if dataset_format == "jsonl_chat":
        return render_training_corpus_jsonl(select_split_examples(payload, subset), mode="chat")
    if dataset_format == "jsonl_completion":
        return render_training_corpus_jsonl(
            select_split_examples(payload, subset),
            mode="completion",
        )
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_split_text(payload)


def render_training_fine_tune_bundle(bundle, output_format: str) -> str:
    payload = serialize_training_fine_tune_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_fine_tune_bundle_text(payload)


def render_training_evaluation_report(report, output_format: str) -> str:
    payload = serialize_training_evaluation_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_evaluation_report_text(payload)


def render_training_evaluation_leaderboard(leaderboard, output_format: str) -> str:
    payload = serialize_training_evaluation_leaderboard(leaderboard)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_evaluation_leaderboard_text(payload)


def render_prompt_patch_plan(plan, output_format: str) -> str:
    payload = serialize_prompt_patch_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_prompt_patch_plan_text(payload)


def render_training_evaluation_comparison(comparison, output_format: str) -> str:
    payload = serialize_training_evaluation_comparison(comparison)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_evaluation_comparison_text(payload)


def render_training_optimizer_leaderboard(leaderboard, output_format: str) -> str:
    payload = serialize_training_optimizer_leaderboard(leaderboard)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_optimizer_leaderboard_text(payload)


def render_training_optimizer_sweep_report(report, output_format: str) -> str:
    payload = serialize_training_optimizer_sweep_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)
    return render_training_optimizer_sweep_report_text(payload)

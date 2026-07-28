"""Training corpus and evaluation CLI handlers."""

from __future__ import annotations

import argparse

from cli_app.renderers import (
    render_prompt_patch_plan as _render_prompt_patch_plan,
    render_training_corpus as _render_training_corpus,
    render_training_evaluation_comparison as _render_training_evaluation_comparison,
    render_training_evaluation_leaderboard as _render_training_evaluation_leaderboard,
    render_training_evaluation_report as _render_training_evaluation_report,
    render_training_fine_tune_bundle as _render_training_fine_tune_bundle,
    render_training_manifest as _render_training_manifest,
    render_training_optimizer_leaderboard as _render_training_optimizer_leaderboard,
    render_training_optimizer_sweep_report as _render_training_optimizer_sweep_report,
    render_training_split as _render_training_split,
)
from cli_app.runtime import CliRuntime


def _build_training_split(args: argparse.Namespace, runtime: CliRuntime):
    return runtime.training_corpus_service.build_split(
        limit=args.limit,
        source=args.source,
        validation_ratio=args.validation_ratio,
    )


def _select_training_examples(split, subset: str):
    return split.train_examples if subset == "train" else split.validation_examples


def _build_prompt_patch_instructions(args: argparse.Namespace, runtime: CliRuntime) -> tuple[str, ...]:
    reports = runtime.training_eval_service.load_history(history_path=args.history_file)
    patch_plan = runtime.training_eval_service.build_prompt_patch_plan(
        reports=reports,
        subset=args.subset,
        model=args.model,
        limit=args.patch_limit,
    )
    return tuple(suggestion.instruction for suggestion in patch_plan.suggestions)


def handle_training_command(args: argparse.Namespace, runtime: CliRuntime) -> int | None:
    """Handle training corpus, eval, leaderboard, and optimizer commands."""
    if args.command == "training-corpus":
        corpus = runtime.training_corpus_service.build_corpus(
            limit=args.limit,
            source=args.source,
        )
        print(_render_training_corpus(corpus, args.format, args.dataset_format))
        return 0
    if args.command == "training-manifest":
        manifest = runtime.training_corpus_service.build_manifest(
            limit=args.limit,
            source=args.source,
        )
        print(_render_training_manifest(manifest, args.format))
        return 0
    if args.command == "training-split":
        split = _build_training_split(args, runtime)
        print(_render_training_split(split, args.format, args.dataset_format, args.subset))
        return 0
    if args.command == "training-bundle":
        bundle = runtime.training_fine_tune_service.build_bundle(
            output_dir=args.output_dir,
            limit=args.limit,
            source=args.source,
            validation_ratio=args.validation_ratio,
            model_family=args.model_family,
        )
        print(_render_training_fine_tune_bundle(bundle, args.format))
        return 0
    if args.command == "training-eval":
        extra_instructions: tuple[str, ...] = ()
        if args.apply_history_patches:
            extra_instructions = _build_prompt_patch_instructions(args, runtime)
        split = _build_training_split(args, runtime)
        examples = _select_training_examples(split, args.subset)
        report = runtime.training_eval_service.evaluate(
            model=args.model,
            examples=examples,
            subset=args.subset,
            extra_instructions=extra_instructions,
        )
        runtime.training_eval_service.append_report(
            report=report,
            history_path=args.history_file,
        )
        print(_render_training_evaluation_report(report, args.format))
        return 0
    if args.command == "training-eval-compare":
        split = _build_training_split(args, runtime)
        examples = _select_training_examples(split, args.subset)
        reports = runtime.training_eval_service.load_history(history_path=args.history_file)
        patch_plan = runtime.training_eval_service.build_prompt_patch_plan(
            reports=reports,
            subset=args.subset,
            model=args.model,
            limit=args.patch_limit,
        )
        baseline_report = runtime.training_eval_service.evaluate(
            model=args.model,
            examples=examples,
            subset=args.subset,
        )
        optimized_report = runtime.training_eval_service.evaluate(
            model=args.model,
            examples=examples,
            subset=args.subset,
            extra_instructions=tuple(
                suggestion.instruction for suggestion in patch_plan.suggestions
            ),
        )
        comparison = runtime.training_eval_service.compare_reports(
            model=args.model,
            subset=args.subset,
            baseline_report=baseline_report,
            optimized_report=optimized_report,
            optimized_prompt_plan=patch_plan,
        )
        runtime.training_eval_service.append_comparison(
            comparison=comparison,
            history_path=args.compare_history_file,
        )
        print(_render_training_evaluation_comparison(comparison, args.format))
        return 0
    if args.command == "training-leaderboard":
        reports = runtime.training_eval_service.load_history(history_path=args.history_file)
        leaderboard = runtime.training_eval_service.build_leaderboard(
            reports=reports,
            subset=args.subset,
        )
        print(_render_training_evaluation_leaderboard(leaderboard, args.format))
        return 0
    if args.command == "training-prompt-patches":
        reports = runtime.training_eval_service.load_history(history_path=args.history_file)
        plan = runtime.training_eval_service.build_prompt_patch_plan(
            reports=reports,
            subset=args.subset,
            model=args.model,
            limit=args.limit,
        )
        print(_render_prompt_patch_plan(plan, args.format))
        return 0
    if args.command == "training-optimizer-leaderboard":
        comparisons = runtime.training_eval_service.load_comparison_history(
            history_path=args.compare_history_file,
        )
        leaderboard = runtime.training_eval_service.build_optimizer_leaderboard(
            comparisons=comparisons,
            subset=args.subset,
            model=args.model,
        )
        print(_render_training_optimizer_leaderboard(leaderboard, args.format))
        return 0
    if args.command == "training-optimizer-sweep":
        split = _build_training_split(args, runtime)
        examples = _select_training_examples(split, args.subset)
        history_reports = runtime.training_eval_service.load_history(
            history_path=args.history_file,
        )
        sweep = runtime.training_eval_service.run_optimizer_sweep(
            models=tuple(args.model),
            examples=examples,
            subset=args.subset,
            history_reports=history_reports,
            patch_limit=args.patch_limit,
        )
        for comparison in sweep.comparisons:
            runtime.training_eval_service.append_comparison(
                comparison=comparison,
                history_path=args.compare_history_file,
            )
        print(_render_training_optimizer_sweep_report(sweep, args.format))
        return 0
    return None

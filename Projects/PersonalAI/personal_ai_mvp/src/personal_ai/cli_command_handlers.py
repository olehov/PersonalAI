"""Grouped command handlers for the PersonalAI CLI."""

from __future__ import annotations

import argparse

from personal_ai.cli_renderers import (
    render_agent_history as _render_agent_history,
    render_agent_runtime_artifact as _render_agent_runtime_artifact,
    render_answer_bundle as _render_answer_bundle,
    render_applied_note_change as _render_applied_note_change,
    render_benchmark_compare_result as _render_benchmark_compare_result,
    render_benchmark_history as _render_benchmark_history,
    render_benchmark_pack as _render_benchmark_pack,
    render_benchmark_run_result as _render_benchmark_run_result,
    render_directory_analysis_report as _render_directory_analysis_report,
    render_generated_answer as _render_generated_answer,
    render_generated_note_application as _render_generated_note_application,
    render_generated_note_draft as _render_generated_note_draft,
    render_maintenance_draft_plan as _render_maintenance_draft_plan,
    render_maintenance_plan as _render_maintenance_plan,
    render_maintenance_report as _render_maintenance_report,
    render_note_change_proposal as _render_note_change_proposal,
    render_note_detail as _render_note_detail,
    render_note_list as _render_note_list,
    render_prompt_patch_plan as _render_prompt_patch_plan,
    render_query_history as _render_query_history,
    render_retrieval_bundle as _render_retrieval_bundle,
    render_scan as _render_scan,
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
from personal_ai.cli_runtime import CliRuntime


def _resolve_note_action(action: str) -> str | None:
    return None if action == "auto" else action


def _build_note_proposal(
    args: argparse.Namespace,
    runtime: CliRuntime,
    *,
    read_content_input,
):
    return runtime.mutation_service.propose_change(
        title=args.title,
        proposed_content=read_content_input(args),
        action=_resolve_note_action(args.action),
        target_dir=args.target_dir,
        target_path=args.target_path,
    )


def _build_note_draft(args: argparse.Namespace, runtime: CliRuntime):
    return runtime.draft_service.draft_note(
        title=args.title,
        instruction=args.instruction,
        model=args.model,
        action=_resolve_note_action(args.action),
        target_dir=args.target_dir,
        target_path=args.target_path,
        scope_dirs=tuple(args.scope_dir),
    )


def _find_maintenance_finding(args: argparse.Namespace, runtime: CliRuntime):
    return runtime.maintenance_service.find_finding(args.note, kind=args.kind)


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


def handle_basic_command(args: argparse.Namespace, runtime: CliRuntime) -> int | None:
    """Handle scan/retrieval/history-style commands."""
    if args.command == "scan":
        print(_render_scan(runtime.knowledge_service.scan_summary(), args.format))
        return 0
    if args.command == "list":
        print(_render_note_list(runtime.knowledge_service.list_notes(), args.format))
        return 0
    if args.command == "analyze-dir":
        report = runtime.directory_analysis_service.analyze_directory(args.directory)
        print(_render_directory_analysis_report(report, args.format))
        return 0
    if args.command == "search":
        print(_render_note_list(runtime.knowledge_service.search_notes(args.query), args.format))
        return 0
    if args.command == "related":
        print(_render_note_list(runtime.knowledge_service.get_related_notes(args.note), args.format))
        return 0
    if args.command == "show":
        note = runtime.knowledge_service.get_note(args.note)
        if note is None:
            print(f"Note not found: {args.note}")
            return 1
        print(_render_note_detail(note, args.format))
        return 0
    if args.command == "retrieve":
        bundle = runtime.retrieval_service.build_context(args.question, scope_dirs=tuple(args.scope_dir))
        print(_render_retrieval_bundle(bundle, args.format))
        return 0
    if args.command == "answer":
        bundle = runtime.answer_service.prepare_answer(args.question, scope_dirs=tuple(args.scope_dir))
        print(_render_answer_bundle(bundle, args.format))
        return 0
    if args.command == "ask":
        generated = runtime.chat_service.ask(
            args.question,
            model=args.model,
            scope_dirs=tuple(args.scope_dir),
        )
        print(_render_generated_answer(generated, args.format))
        return 0
    if args.command == "agent-runtime":
        artifact = runtime.agent_runtime_service.run(
            args.request_text,
            model=args.model,
            scope_dirs=tuple(args.scope_dir),
        )
        print(_render_agent_runtime_artifact(artifact, args.format))
        return 0
    if args.command == "history":
        entries = runtime.history_repository.list_entries(limit=args.limit)
        print(_render_query_history(entries, args.format))
        return 0
    if args.command == "agent-history":
        entries = runtime.history_repository.list_agent_runs(limit=args.limit)
        print(_render_agent_history(entries, args.format))
        return 0
    return None


def handle_benchmark_command(args: argparse.Namespace, runtime: CliRuntime) -> int | None:
    """Handle benchmark pack/run/history/compare commands."""
    if args.command == "benchmark-pack":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        print(_render_benchmark_pack(pack, args.format, task_id=args.task_id))
        return 0
    if args.command == "benchmark-run":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        task = next((item for item in pack.tasks if item.task_id == args.task_id), None)
        if task is None:
            print(f"Benchmark task not found: {args.task_id}")
            return 1
        result = runtime.benchmark_run_service.run_task(
            pack_id=pack.pack_id,
            task=task,
            model=args.model,
        )
        print(_render_benchmark_run_result(result, args.format))
        return 0
    if args.command == "benchmark-history":
        entries = runtime.history_repository.list_benchmark_runs(limit=args.limit)
        print(_render_benchmark_history(entries, args.format))
        return 0
    if args.command == "benchmark-compare":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        if args.task_id:
            tasks = tuple(item for item in pack.tasks if item.task_id == args.task_id)
            if not tasks:
                print(f"Benchmark task not found: {args.task_id}")
                return 1
        else:
            tasks = pack.tasks
        comparison = runtime.benchmark_run_service.compare_models(
            pack_id=pack.pack_id,
            tasks=tasks,
            models=tuple(args.models),
        )
        print(_render_benchmark_compare_result(comparison, args.format))
        return 0
    return None


def handle_note_command(
    args: argparse.Namespace,
    runtime: CliRuntime,
    *,
    read_content_input,
) -> int | None:
    """Handle safe note proposal/write/draft commands."""
    if args.command == "propose-note":
        proposal = _build_note_proposal(args, runtime, read_content_input=read_content_input)
        print(_render_note_change_proposal(proposal, args.format))
        return 0
    if args.command == "write-note":
        proposal = _build_note_proposal(args, runtime, read_content_input=read_content_input)
        if proposal.warnings:
            print(_render_note_change_proposal(proposal, args.format))
            return 1
        applied = runtime.mutation_service.apply_change(proposal, approved=args.approve)
        print(_render_applied_note_change(proposal, applied, args.format))
        return 0
    if args.command == "draft-note":
        draft = _build_note_draft(args, runtime)
        print(_render_generated_note_draft(draft, args.format))
        return 0
    if args.command == "draft-write-note":
        draft = _build_note_draft(args, runtime)
        if draft.proposal.warnings:
            print(_render_generated_note_draft(draft, args.format))
            return 1
        applied = runtime.mutation_service.apply_change(draft.proposal, approved=args.approve)
        print(_render_generated_note_application(draft, applied, args.format))
        return 0
    return None


def handle_maintenance_command(args: argparse.Namespace, runtime: CliRuntime) -> int | None:
    """Handle maintenance inspection and maintenance-draft commands."""
    if args.command == "maintenance":
        report = runtime.maintenance_service.inspect()
        print(_render_maintenance_report(report, args.format))
        return 0
    if args.command == "maintenance-plan":
        plan = runtime.maintenance_service.build_plan(
            limit=args.limit,
            kinds=tuple(args.kind),
        )
        print(_render_maintenance_plan(plan, args.format))
        return 0
    if args.command == "maintenance-plan-draft":
        plan = runtime.maintenance_service.build_plan(
            limit=args.limit,
            kinds=tuple(args.kind),
        )
        draft_plan = runtime.draft_service.draft_maintenance_plan(
            plan=plan,
            model=args.model,
        )
        print(_render_maintenance_draft_plan(draft_plan, args.format))
        return 0
    if args.command == "maintenance-draft":
        finding = _find_maintenance_finding(args, runtime)
        if finding is None:
            print(f"Maintenance finding not found for note: {args.note}")
            return 1
        draft = runtime.draft_service.draft_maintenance_finding(
            finding=finding,
            model=args.model,
        )
        print(_render_generated_note_draft(draft, args.format))
        return 0
    if args.command == "maintenance-draft-write":
        finding = _find_maintenance_finding(args, runtime)
        if finding is None:
            print(f"Maintenance finding not found for note: {args.note}")
            return 1
        draft = runtime.draft_service.draft_maintenance_finding(
            finding=finding,
            model=args.model,
        )
        if draft.proposal.warnings:
            print(_render_generated_note_draft(draft, args.format))
            return 1
        applied = runtime.mutation_service.apply_change(draft.proposal, approved=args.approve)
        print(_render_generated_note_application(draft, applied, args.format))
        return 0
    return None


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

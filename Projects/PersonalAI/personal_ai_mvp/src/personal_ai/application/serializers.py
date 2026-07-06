"""JSON-friendly serializers for application/domain payloads."""

from __future__ import annotations

from dataclasses import asdict

from personal_ai.domain.models import (
    AgentRunHistoryEntry,
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    AgentRuntimeArtifact,
    AgentRuntimeStep,
    AgentRuntimeTaskPlan,
    AgentRuntimeTaskPlanEntry,
    AppliedNoteChange,
    BenchmarkRunHistoryEntry,
    DirectoryAnalysisNodeStat,
    DirectoryAnalysisReport,
    DirectoryCoverageSuggestion,
    GeneratedAnswer,
    GeneratedNoteDraft,
    KnowledgeMaintenanceFinding,
    KnowledgeMaintenancePlan,
    KnowledgeMaintenancePlanEntry,
    KnowledgeMaintenanceReport,
    MaintenanceDraftPlan,
    MaintenanceDraftPlanEntry,
    NoteChangeProposal,
    NoteDocument,
    PromptPatchPlan,
    PromptPatchSuggestion,
    QueryHistoryEntry,
    RetrievalBundle,
    RetrievedNote,
    TrainingCorpus,
    TrainingCorpusManifest,
    TrainingCorpusSplit,
    TrainingEvaluationComparison,
    TrainingEvaluationExampleResult,
    TrainingEvaluationFailureSnapshot,
    TrainingEvaluationLeaderboard,
    TrainingEvaluationLeaderboardEntry,
    TrainingEvaluationReport,
    TrainingExample,
    TrainingFineTuneBundle,
    TrainingFineTuneRecipe,
    TrainingOptimizerLeaderboard,
    TrainingOptimizerLeaderboardEntry,
    TrainingOptimizerSweepReport,
    TrainingTrainerArtifact,
    AnswerBundle,
)


def serialize_note(note: NoteDocument) -> dict[str, object]:
    """Converts a note to a JSON-friendly dictionary."""
    if hasattr(note, "__dataclass_fields__"):
        payload = asdict(note)
        payload["path"] = note.path.as_posix()
        return payload

    metadata = getattr(getattr(note, "metadata", None), "values", {})
    links = [
        {
            "raw": getattr(link, "raw", ""),
            "target": getattr(link, "target", ""),
            "alias": getattr(link, "alias", None),
        }
        for link in getattr(note, "links", ())
    ]
    return {
        "path": note.path.as_posix(),
        "title": getattr(note, "title", ""),
        "content": getattr(note, "content", ""),
        "metadata": {"values": metadata},
        "links": links,
    }


def serialize_retrieved_note(item: RetrievedNote) -> dict[str, object]:
    """Converts a retrieved note to a JSON-friendly dictionary."""
    return {
        "score": item.score,
        "reason": item.reason,
        "note": serialize_note(item.note),
    }


def serialize_retrieval_bundle(bundle: RetrievalBundle) -> dict[str, object]:
    """Converts a retrieval bundle to a JSON-friendly dictionary."""
    return {
        "question": bundle.question,
        "primary_notes": [serialize_retrieved_note(item) for item in bundle.primary_notes],
        "related_notes": [serialize_retrieved_note(item) for item in bundle.related_notes],
    }


def serialize_answer_bundle(bundle: AnswerBundle) -> dict[str, object]:
    """Converts an answer bundle to a JSON-friendly dictionary."""
    return {
        "question": bundle.question,
        "task_mode": bundle.task_mode,
        "citations": list(bundle.citations),
        "retrieval": serialize_retrieval_bundle(bundle.retrieval),
        "messages": [
            {"role": message.role, "content": message.content}
            for message in bundle.messages
        ],
    }


def serialize_directory_analysis_node_stat(item: DirectoryAnalysisNodeStat) -> dict[str, object]:
    """Converts a directory graph node stat to a JSON-friendly dictionary."""
    return {
        "note": serialize_note(item.note),
        "inbound_links": item.inbound_links,
        "outbound_links": item.outbound_links,
    }


def serialize_directory_coverage_suggestion(
    suggestion: DirectoryCoverageSuggestion,
) -> dict[str, object]:
    """Converts a directory coverage suggestion to a JSON-friendly dictionary."""
    return {
        "title": suggestion.title,
        "reason": suggestion.reason,
        "source": suggestion.source,
    }


def serialize_directory_analysis_report(report: DirectoryAnalysisReport) -> dict[str, object]:
    """Converts a directory analysis report to a JSON-friendly dictionary."""
    return {
        "directory": report.directory.as_posix(),
        "note_count": report.note_count,
        "notes": [serialize_note(note) for note in report.notes],
        "total_links": report.total_links,
        "internal_link_count": report.internal_link_count,
        "cross_directory_link_count": report.cross_directory_link_count,
        "unresolved_links": list(report.unresolved_links),
        "isolated_notes": [path.as_posix() for path in report.isolated_notes],
        "hub_notes": [serialize_directory_analysis_node_stat(item) for item in report.hub_notes],
        "suggestions": [
            serialize_directory_coverage_suggestion(suggestion)
            for suggestion in report.suggestions
        ],
    }


def serialize_generated_answer(answer: GeneratedAnswer) -> dict[str, object]:
    """Converts a generated answer to a JSON-friendly dictionary."""
    return {
        "model": answer.model,
        "question": answer.question,
        "answer_text": answer.answer_text,
        "citations": list(answer.citations),
        "prompt": serialize_answer_bundle(answer.prompt) if answer.prompt is not None else None,
    }


def serialize_agent_runtime_step(step: AgentRuntimeStep) -> dict[str, object]:
    """Converts an agent runtime step to a JSON-friendly dictionary."""
    return {
        "step_index": step.step_index,
        "kind": step.kind,
        "title": step.title,
        "input_text": step.input_text,
        "output_text": step.output_text,
        "observation": step.observation,
    }


def serialize_agent_runtime_action(action: AgentRuntimeAction) -> dict[str, object]:
    """Converts a recommended runtime action to a JSON-friendly dictionary."""
    return {
        "action_type": action.action_type,
        "title": action.title,
        "target": action.target,
        "instruction": action.instruction,
        "rationale": action.rationale,
    }


def serialize_agent_runtime_action_execution(
    execution: AgentRuntimeActionExecution,
) -> dict[str, object]:
    """Converts an executed runtime action to a JSON-friendly dictionary."""
    return {
        "action_type": execution.action_type,
        "target": execution.target,
        "status": execution.status,
        "output_text": execution.output_text,
    }


def serialize_agent_runtime_task_plan_entry(
    entry: AgentRuntimeTaskPlanEntry,
) -> dict[str, object]:
    """Converts one structured task-plan entry to a JSON-friendly dictionary."""
    return {
        "step_index": entry.step_index,
        "title": entry.title,
        "status": entry.status,
        "details": entry.details,
        "source_section": entry.source_section,
    }


def serialize_agent_runtime_task_plan(
    plan: AgentRuntimeTaskPlan,
) -> dict[str, object]:
    """Converts a structured task plan to a JSON-friendly dictionary."""
    return {
        "goal": plan.goal,
        "current_focus": plan.current_focus,
        "summary": plan.summary,
        "entries": [
            serialize_agent_runtime_task_plan_entry(entry)
            for entry in plan.entries
        ],
        "validation_checks": list(plan.validation_checks),
    }


def serialize_agent_runtime_artifact(artifact: AgentRuntimeArtifact) -> dict[str, object]:
    """Converts an agent runtime artifact to a JSON-friendly dictionary."""
    action_executions = tuple(getattr(artifact, "action_executions", ()))
    recommended_actions = tuple(getattr(artifact, "recommended_actions", ()))
    task_plan = getattr(artifact, "task_plan", None)
    executed_actions = sum(
        1 for execution in action_executions if execution.status == "executed"
    )
    deferred_actions = sum(
        1 for execution in action_executions if execution.status == "deferred"
    )
    failed_actions = sum(
        1 for execution in action_executions if execution.status == "failed"
    )
    return {
        "generated_at": artifact.generated_at.isoformat(),
        "history_entry_id": getattr(artifact, "history_entry_id", None),
        "model": artifact.model,
        "executor_model": getattr(artifact, "executor_model", None),
        "critic_model": getattr(artifact, "critic_model", None),
        "synthesis_model": getattr(artifact, "synthesis_model", None),
        "discussion_preset": getattr(artifact, "discussion_preset", None),
        "request_text": artifact.request_text,
        "normalized_goal": artifact.normalized_goal,
        "task_mode": artifact.task_mode,
        "status": artifact.status,
        "scope_dirs": list(artifact.scope_dirs),
        "citations": list(artifact.citations),
        "overview": {
            "step_count": len(artifact.steps),
            "recommended_action_count": len(recommended_actions),
            "executed_action_count": executed_actions,
            "deferred_action_count": deferred_actions,
            "failed_action_count": failed_actions,
            "citation_count": len(artifact.citations),
            "planned_task_count": len(task_plan.entries) if task_plan is not None else 0,
            "planner_model": artifact.model,
            "executor_model": getattr(artifact, "executor_model", None),
            "critic_model": getattr(artifact, "critic_model", None),
            "synthesis_model": getattr(artifact, "synthesis_model", None),
            "discussion_preset": getattr(artifact, "discussion_preset", None),
        },
        "steps": [serialize_agent_runtime_step(step) for step in artifact.steps],
        "recommended_actions": [
            serialize_agent_runtime_action(action)
            for action in recommended_actions
        ],
        "action_executions": [
            serialize_agent_runtime_action_execution(execution)
            for execution in action_executions
        ],
        "task_plan": (
            serialize_agent_runtime_task_plan(task_plan)
            if task_plan is not None
            else None
        ),
        "discussion_trace": (
            {
                "preset": artifact.discussion_trace.preset,
                "planner_draft": artifact.discussion_trace.planner_draft,
                "critic_feedback": artifact.discussion_trace.critic_feedback,
                "synthesis_output": artifact.discussion_trace.synthesis_output,
                "fallback_used": artifact.discussion_trace.fallback_used,
            }
            if getattr(artifact, "discussion_trace", None) is not None
            else None
        ),
        "final_output": artifact.final_output,
        "prompt": (
            serialize_answer_bundle(artifact.prompt)
            if artifact.prompt is not None
            else None
        ),
    }


def serialize_agent_run_history_entry(entry: AgentRunHistoryEntry) -> dict[str, object]:
    """Converts an agent run history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "request_text": entry.request_text,
        "normalized_goal": entry.normalized_goal,
        "model": entry.model,
        "task_mode": entry.task_mode,
        "status": entry.status,
        "scope_dirs": list(entry.scope_dirs),
        "citations": list(entry.citations),
        "latency_ms": entry.latency_ms,
        "artifact_payload": entry.artifact_payload,
    }


def serialize_query_history_entry(entry: QueryHistoryEntry) -> dict[str, object]:
    """Converts a query history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "question": entry.question,
        "answer_text": entry.answer_text,
        "model": entry.model,
        "task_mode": entry.task_mode,
        "scope_dirs": list(entry.scope_dirs),
        "citations": list(entry.citations),
        "latency_ms": entry.latency_ms,
        "prompt_payload": entry.prompt_payload,
    }


def serialize_benchmark_run_history_entry(entry: BenchmarkRunHistoryEntry) -> dict[str, object]:
    """Converts a benchmark run history entry to a JSON-friendly dictionary."""
    return {
        "entry_id": entry.entry_id,
        "created_at": entry.created_at.isoformat(),
        "pack_id": entry.pack_id,
        "task_id": entry.task_id,
        "category": entry.category,
        "workflow": entry.workflow,
        "model": entry.model,
        "status": entry.status,
        "scope_dirs": list(entry.scope_dirs),
        "prompt_text": entry.prompt_text,
        "latency_ms": entry.latency_ms,
        "result_payload": entry.result_payload,
    }


def serialize_note_change_proposal(proposal: NoteChangeProposal) -> dict[str, object]:
    """Converts a note change proposal to a JSON-friendly dictionary."""
    return {
        "action": proposal.action,
        "target_path": proposal.target_path.as_posix(),
        "title": proposal.title,
        "reason": proposal.reason,
        "proposed_content": proposal.proposed_content,
        "current_content": proposal.current_content,
        "archive_path": proposal.archive_path.as_posix() if proposal.archive_path else None,
        "similar_notes": list(proposal.similar_notes),
        "warnings": list(proposal.warnings),
        "created_at": proposal.created_at.isoformat(),
    }


def serialize_applied_note_change(change: AppliedNoteChange) -> dict[str, object]:
    """Converts an applied note change to a JSON-friendly dictionary."""
    return {
        "action": change.action,
        "target_path": change.target_path.as_posix(),
        "backup_path": change.backup_path.as_posix() if change.backup_path else None,
        "archive_path": change.archive_path.as_posix() if change.archive_path else None,
        "applied_at": change.applied_at.isoformat(),
    }


def serialize_generated_note_draft(draft: GeneratedNoteDraft) -> dict[str, object]:
    """Converts a generated note draft to a JSON-friendly dictionary."""
    companion_proposals = getattr(draft, "companion_proposals", ())
    return {
        "model": draft.model,
        "title": draft.title,
        "instruction": draft.instruction,
        "content": draft.content,
        "citations": list(draft.citations),
        "proposal": serialize_note_change_proposal(draft.proposal),
        "companion_proposals": [
            serialize_note_change_proposal(proposal)
            for proposal in companion_proposals
        ],
        "prompt": serialize_answer_bundle(draft.prompt) if draft.prompt is not None else None,
    }


def serialize_maintenance_finding(finding: KnowledgeMaintenanceFinding) -> dict[str, object]:
    """Converts a maintenance finding to a JSON-friendly dictionary."""
    return {
        "kind": finding.kind,
        "summary": finding.summary,
        "details": list(finding.details),
        "note": serialize_note(finding.note),
        "proposal": (
            serialize_note_change_proposal(finding.proposal)
            if finding.proposal is not None
            else None
        ),
    }


def serialize_maintenance_report(report: KnowledgeMaintenanceReport) -> dict[str, object]:
    """Converts a maintenance report to a JSON-friendly dictionary."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "findings": [serialize_maintenance_finding(finding) for finding in report.findings],
    }


def serialize_maintenance_plan_entry(entry: KnowledgeMaintenancePlanEntry) -> dict[str, object]:
    """Converts a maintenance plan entry to a JSON-friendly dictionary."""
    return {
        "finding": serialize_maintenance_finding(entry.finding),
        "proposal": serialize_note_change_proposal(entry.proposal),
        "merged_kinds": list(entry.merged_kinds),
    }


def serialize_maintenance_plan(plan: KnowledgeMaintenancePlan) -> dict[str, object]:
    """Converts a maintenance batch plan to a JSON-friendly dictionary."""
    return {
        "generated_at": plan.generated_at.isoformat(),
        "entries": [serialize_maintenance_plan_entry(entry) for entry in plan.entries],
        "skipped_paths": list(plan.skipped_paths),
    }


def serialize_maintenance_draft_plan_entry(entry: MaintenanceDraftPlanEntry) -> dict[str, object]:
    """Converts a maintenance draft plan entry to a JSON-friendly dictionary."""
    return {
        "plan_entry": serialize_maintenance_plan_entry(entry.plan_entry),
        "draft": serialize_generated_note_draft(entry.draft),
    }


def serialize_maintenance_draft_plan(plan: MaintenanceDraftPlan) -> dict[str, object]:
    """Converts a maintenance draft batch to a JSON-friendly dictionary."""
    return {
        "generated_at": plan.generated_at.isoformat(),
        "entries": [serialize_maintenance_draft_plan_entry(entry) for entry in plan.entries],
    }


def serialize_training_example(example: TrainingExample) -> dict[str, object]:
    """Converts a training example to a JSON-friendly dictionary."""
    return {
        "example_id": example.example_id,
        "source": example.source,
        "quality_tier": example.quality_tier,
        "task": example.task,
        "source_note_path": example.source_note_path.as_posix(),
        "title": example.title,
        "instruction": example.instruction,
        "input_markdown": example.input_markdown,
        "target_markdown": example.target_markdown,
        "tags": list(example.tags),
    }


def serialize_training_corpus(corpus: TrainingCorpus) -> dict[str, object]:
    """Converts a training corpus to a JSON-friendly dictionary."""
    return {
        "generated_at": corpus.generated_at.isoformat(),
        "examples": [serialize_training_example(example) for example in corpus.examples],
    }


def serialize_training_manifest(manifest: TrainingCorpusManifest) -> dict[str, object]:
    """Converts a training corpus manifest to a JSON-friendly dictionary."""
    return {
        "generated_at": manifest.generated_at.isoformat(),
        "total_examples": manifest.total_examples,
        "by_source": dict(manifest.by_source),
        "by_quality_tier": dict(manifest.by_quality_tier),
        "by_task": dict(manifest.by_task),
    }


def serialize_training_split(split: TrainingCorpusSplit) -> dict[str, object]:
    """Converts a training split to a JSON-friendly dictionary."""
    return {
        "generated_at": split.generated_at.isoformat(),
        "policy": split.policy,
        "train_examples": [serialize_training_example(example) for example in split.train_examples],
        "validation_examples": [
            serialize_training_example(example) for example in split.validation_examples
        ],
    }


def serialize_training_fine_tune_recipe(recipe: TrainingFineTuneRecipe) -> dict[str, object]:
    """Converts a fine-tuning recipe to a JSON-friendly dictionary."""
    return {
        "model_family": recipe.model_family,
        "dataset_format": recipe.dataset_format,
        "recommended_framework": recipe.recommended_framework,
        "learning_rate": recipe.learning_rate,
        "num_epochs": recipe.num_epochs,
        "micro_batch_size": recipe.micro_batch_size,
        "gradient_accumulation_steps": recipe.gradient_accumulation_steps,
        "lora_rank": recipe.lora_rank,
        "lora_alpha": recipe.lora_alpha,
        "lora_dropout": recipe.lora_dropout,
        "max_sequence_length": recipe.max_sequence_length,
        "notes": list(recipe.notes),
    }


def serialize_training_trainer_artifact(
    artifact: TrainingTrainerArtifact,
) -> dict[str, object]:
    """Converts a trainer artifact to a JSON-friendly dictionary."""
    return {
        "trainer": artifact.trainer,
        "kind": artifact.kind,
        "path": artifact.path.as_posix(),
        "format": artifact.format,
    }


def serialize_training_fine_tune_bundle(
    bundle: TrainingFineTuneBundle,
) -> dict[str, object]:
    """Converts a persisted fine-tuning bundle to a JSON-friendly dictionary."""
    return {
        "generated_at": bundle.generated_at.isoformat(),
        "bundle_dir": bundle.bundle_dir.as_posix(),
        "train_path": bundle.train_path.as_posix(),
        "validation_path": bundle.validation_path.as_posix(),
        "manifest_path": bundle.manifest_path.as_posix(),
        "recipe_path": bundle.recipe_path.as_posix(),
        "runbook_path": bundle.runbook_path.as_posix(),
        "trainer_artifacts": [
            serialize_training_trainer_artifact(artifact)
            for artifact in bundle.trainer_artifacts
        ],
        "source": bundle.source,
        "validation_ratio": bundle.validation_ratio,
        "train_examples": bundle.train_examples,
        "validation_examples": bundle.validation_examples,
        "recipe": serialize_training_fine_tune_recipe(bundle.recipe),
    }


def serialize_training_evaluation_example_result(
    result: TrainingEvaluationExampleResult,
) -> dict[str, object]:
    """Converts a training evaluation example result to a JSON-friendly dictionary."""
    return {
        "example_id": result.example_id,
        "source_note_path": result.source_note_path.as_posix(),
        "source": result.source,
        "quality_tier": result.quality_tier,
        "task": result.task,
        "model": result.model,
        "score": result.score,
        "exact_match": result.exact_match,
        "target_link_count": result.target_link_count,
        "output_link_count": result.output_link_count,
        "target_heading_count": result.target_heading_count,
        "output_heading_count": result.output_heading_count,
        "output_markdown": result.output_markdown,
    }


def serialize_training_evaluation_failure_snapshot(
    snapshot: TrainingEvaluationFailureSnapshot,
) -> dict[str, object]:
    """Converts a failure snapshot to a JSON-friendly dictionary."""
    return {
        "example_id": snapshot.example_id,
        "source_note_path": snapshot.source_note_path.as_posix(),
        "task": snapshot.task,
        "score": snapshot.score,
        "exact_match": snapshot.exact_match,
        "output_markdown_preview": snapshot.output_markdown_preview,
        "error_tags": list(snapshot.error_tags),
    }


def serialize_prompt_patch_suggestion(
    suggestion: PromptPatchSuggestion,
) -> dict[str, object]:
    """Converts a prompt patch suggestion to a JSON-friendly dictionary."""
    return {
        "error_tag": suggestion.error_tag,
        "occurrences": suggestion.occurrences,
        "instruction": suggestion.instruction,
        "rationale": suggestion.rationale,
    }


def serialize_prompt_patch_plan(
    plan: PromptPatchPlan,
) -> dict[str, object]:
    """Converts a prompt patch plan to a JSON-friendly dictionary."""
    return {
        "generated_at": plan.generated_at.isoformat(),
        "base_system_prompt": plan.base_system_prompt,
        "optimized_system_prompt": plan.optimized_system_prompt,
        "suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in plan.suggestions
        ],
    }


def serialize_training_evaluation_comparison(
    comparison: TrainingEvaluationComparison,
) -> dict[str, object]:
    """Converts an evaluation comparison to a JSON-friendly dictionary."""
    return {
        "generated_at": comparison.generated_at.isoformat(),
        "model": comparison.model,
        "subset": comparison.subset,
        "score_delta": comparison.score_delta,
        "exact_match_rate_delta": comparison.exact_match_rate_delta,
        "baseline_report": serialize_training_evaluation_report(comparison.baseline_report),
        "optimized_report": serialize_training_evaluation_report(comparison.optimized_report),
        "optimized_prompt_plan": serialize_prompt_patch_plan(comparison.optimized_prompt_plan),
    }


def serialize_training_optimizer_leaderboard_entry(
    entry: TrainingOptimizerLeaderboardEntry,
) -> dict[str, object]:
    """Converts an optimizer leaderboard entry to a JSON-friendly dictionary."""
    return {
        "model": entry.model,
        "subset": entry.subset,
        "runs": entry.runs,
        "average_score_delta": entry.average_score_delta,
        "best_score_delta": entry.best_score_delta,
        "latest_score_delta": entry.latest_score_delta,
        "average_exact_match_rate_delta": entry.average_exact_match_rate_delta,
        "latest_exact_match_rate_delta": entry.latest_exact_match_rate_delta,
        "last_evaluated_at": entry.last_evaluated_at.isoformat(),
    }


def serialize_training_optimizer_leaderboard(
    leaderboard: TrainingOptimizerLeaderboard,
) -> dict[str, object]:
    """Converts an optimizer leaderboard to a JSON-friendly dictionary."""
    return {
        "generated_at": leaderboard.generated_at.isoformat(),
        "total_runs": leaderboard.total_runs,
        "entries": [
            serialize_training_optimizer_leaderboard_entry(entry)
            for entry in leaderboard.entries
        ],
    }


def serialize_training_optimizer_sweep_report(
    report: TrainingOptimizerSweepReport,
) -> dict[str, object]:
    """Converts an optimizer sweep report to a JSON-friendly dictionary."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "subset": report.subset,
        "comparisons": [
            serialize_training_evaluation_comparison(comparison)
            for comparison in report.comparisons
        ],
    }


def serialize_training_evaluation_report(
    report: TrainingEvaluationReport,
) -> dict[str, object]:
    """Converts a training evaluation report to a JSON-friendly dictionary."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "model": report.model,
        "subset": report.subset,
        "average_score": report.average_score,
        "exact_match_rate": report.exact_match_rate,
        "results": [
            serialize_training_evaluation_example_result(result)
            for result in report.results
        ],
        "failure_snapshots": [
            serialize_training_evaluation_failure_snapshot(snapshot)
            for snapshot in report.failure_snapshots
        ],
        "prompt_patch_suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in report.prompt_patch_suggestions
        ],
    }


def serialize_training_evaluation_leaderboard_entry(
    entry: TrainingEvaluationLeaderboardEntry,
) -> dict[str, object]:
    """Converts a leaderboard entry to a JSON-friendly dictionary."""
    return {
        "model": entry.model,
        "subset": entry.subset,
        "runs": entry.runs,
        "average_score": entry.average_score,
        "best_score": entry.best_score,
        "latest_score": entry.latest_score,
        "delta_vs_previous_score": entry.delta_vs_previous_score,
        "delta_vs_best_score": entry.delta_vs_best_score,
        "average_exact_match_rate": entry.average_exact_match_rate,
        "latest_exact_match_rate": entry.latest_exact_match_rate,
        "delta_vs_previous_exact_match_rate": entry.delta_vs_previous_exact_match_rate,
        "delta_vs_best_exact_match_rate": entry.delta_vs_best_exact_match_rate,
        "last_evaluated_at": entry.last_evaluated_at.isoformat(),
        "latest_failure_snapshots": [
            serialize_training_evaluation_failure_snapshot(snapshot)
            for snapshot in entry.latest_failure_snapshots
        ],
        "prompt_patch_suggestions": [
            serialize_prompt_patch_suggestion(suggestion)
            for suggestion in entry.prompt_patch_suggestions
        ],
    }


def serialize_training_evaluation_leaderboard(
    leaderboard: TrainingEvaluationLeaderboard,
) -> dict[str, object]:
    """Converts a training evaluation leaderboard to a JSON-friendly dictionary."""
    return {
        "generated_at": leaderboard.generated_at.isoformat(),
        "total_runs": leaderboard.total_runs,
        "entries": [
            serialize_training_evaluation_leaderboard_entry(entry)
            for entry in leaderboard.entries
        ],
    }

"""Rendering helpers for CLI output."""

from __future__ import annotations

import json

from personal_ai.application import (
    BenchmarkPackService,
    serialize_applied_note_change,
    serialize_agent_run_history_entry,
    serialize_agent_runtime_artifact,
    serialize_answer_bundle,
    serialize_benchmark_run_history_entry,
    serialize_directory_analysis_report,
    serialize_generated_answer,
    serialize_generated_note_draft,
    serialize_maintenance_draft_plan,
    serialize_maintenance_plan,
    serialize_maintenance_report,
    serialize_note,
    serialize_note_change_proposal,
    serialize_prompt_patch_plan,
    serialize_query_history_entry,
    serialize_retrieval_bundle,
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


def render_scan(summary: dict[str, int], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(summary, indent=2)
    return "\n".join(f"{key}: {value}" for key, value in summary.items())


def render_note_list(notes: list, output_format: str) -> str:
    if not notes:
        return "[]" if output_format == "json" else "No notes found."

    if output_format == "json":
        return json.dumps([serialize_note(note) for note in notes], indent=2)

    return "\n".join(f"{note.path.as_posix()} | {note.title}" for note in notes)


def render_note_detail(note, output_format: str) -> str:
    payload = serialize_note(note)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"path: {payload['path']}",
        f"title: {payload['title']}",
        f"metadata: {payload['metadata']['values']}",
        f"links: {len(payload['links'])}",
    ]
    return "\n".join(lines)


def render_retrieval_bundle(bundle, output_format: str) -> str:
    payload = serialize_retrieval_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"question: {payload['question']}", "primary_notes:"]
    if payload["primary_notes"]:
        for item in payload["primary_notes"]:
            lines.append(
                f"- {item['note']['path']} | score={item['score']} | reason={item['reason']}"
            )
    else:
        lines.append("- none")

    lines.append("related_notes:")
    if payload["related_notes"]:
        for item in payload["related_notes"]:
            lines.append(
                f"- {item['note']['path']} | score={item['score']} | reason={item['reason']}"
            )
    else:
        lines.append("- none")

    return "\n".join(lines)


def render_answer_bundle(bundle, output_format: str) -> str:
    payload = serialize_answer_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"question: {payload['question']}", "citations:"]
    if payload["citations"]:
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    else:
        lines.append("- none")

    lines.append("messages:")
    for message in payload["messages"]:
        preview = message["content"].splitlines()[0] if message["content"] else ""
        lines.append(f"- {message['role']}: {preview}")
    return "\n".join(lines)


def render_directory_analysis_report(report, output_format: str) -> str:
    payload = serialize_directory_analysis_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"directory: {payload['directory']}",
        f"note_count: {payload['note_count']}",
        f"total_links: {payload['total_links']}",
        f"internal_link_count: {payload['internal_link_count']}",
        f"cross_directory_link_count: {payload['cross_directory_link_count']}",
        "notes:",
    ]
    if payload["notes"]:
        for note in payload["notes"]:
            lines.append(f"- {note['path']} | {note['title']}")
    else:
        lines.append("- none")

    lines.append("hub_notes:")
    if payload["hub_notes"]:
        for item in payload["hub_notes"]:
            lines.append(
                "- "
                f"{item['note']['path']} | inbound={item['inbound_links']} | "
                f"outbound={item['outbound_links']}"
            )
    else:
        lines.append("- none")

    lines.append("isolated_notes:")
    if payload["isolated_notes"]:
        for path in payload["isolated_notes"]:
            lines.append(f"- {path}")
    else:
        lines.append("- none")

    lines.append("unresolved_links:")
    if payload["unresolved_links"]:
        for target in payload["unresolved_links"]:
            lines.append(f"- {target}")
    else:
        lines.append("- none")

    lines.append("suggestions:")
    if payload["suggestions"]:
        for suggestion in payload["suggestions"]:
            lines.append(
                f"- {suggestion['title']} | {suggestion['source']} | {suggestion['reason']}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines)


def render_generated_answer(answer, output_format: str) -> str:
    payload = serialize_generated_answer(answer)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [f"model: {payload['model']}", f"question: {payload['question']}", "answer:"]
    lines.append(payload["answer_text"])
    lines.append("citations:")
    if payload["citations"]:
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def render_agent_runtime_artifact(artifact, output_format: str) -> str:
    payload = serialize_agent_runtime_artifact(artifact)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    overview = payload.get("overview", {})
    lines = [
        f"model: {payload['model']}",
        f"status: {payload['status']}",
        f"task_mode: {payload['task_mode']}",
        f"normalized_goal: {payload['normalized_goal']}",
        f"scope_dirs: {', '.join(payload['scope_dirs']) if payload['scope_dirs'] else 'none'}",
        (
            "overview: "
            f"steps={overview.get('step_count', 0)} | "
            f"recommended_actions={overview.get('recommended_action_count', 0)} | "
            f"executed={overview.get('executed_action_count', 0)} | "
            f"deferred={overview.get('deferred_action_count', 0)} | "
            f"failed={overview.get('failed_action_count', 0)} | "
            f"citations={overview.get('citation_count', 0)}"
        ),
        "timeline:",
    ]
    for step in payload["steps"]:
        lines.append(
            f"- {step['step_index']}. {step['kind']} | {step['title']}"
        )
        lines.append(f"  observation: {step['observation']}")
    if payload["recommended_actions"]:
        lines.append("recommended_actions:")
        for action in payload["recommended_actions"]:
            lines.append(
                f"- {action['action_type']} | {action['title']} | {action['target']}"
            )
            lines.append(f"  instruction: {action['instruction']}")
    if payload["action_executions"]:
        lines.append("action_executions:")
        for execution in payload["action_executions"]:
            lines.append(
                f"- {execution['action_type']} | {execution['status']} | {execution['target']}"
            )
    lines.extend(
        [
            "final_output:",
            payload["final_output"],
        ]
    )
    if payload["citations"]:
        lines.append("citations:")
        for citation in payload["citations"]:
            lines.append(f"- {citation}")
    return "\n".join(lines)


def render_query_history(entries, output_format: str) -> str:
    payload = [serialize_query_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved query history."

    lines: list[str] = []
    for entry in payload:
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['model']} | "
            f"{entry['task_mode']} | {entry['question']}"
        )
    return "\n".join(lines)


def render_agent_history(entries, output_format: str) -> str:
    payload = [serialize_agent_run_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved agent runtime history."

    lines: list[str] = []
    for entry in payload:
        overview = (
            entry["artifact_payload"].get("overview", {})
            if isinstance(entry.get("artifact_payload"), dict)
            else {}
        )
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['model']} | "
            f"{entry['task_mode']} | {entry['status']} | "
            f"steps={overview.get('step_count', 0)} | "
            f"actions={overview.get('recommended_action_count', 0)} | "
            f"{entry['request_text']}"
        )
    return "\n".join(lines)


def render_benchmark_pack(pack, output_format: str, *, task_id: str | None) -> str:
    payload = BenchmarkPackService().serialize_pack(pack)
    if task_id:
        payload["tasks"] = [
            task for task in payload["tasks"]
            if task["task_id"] == task_id
        ]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"title: {payload['title']}",
        f"description: {payload['description']}",
        f"task_count: {len(payload['tasks'])}",
        "tasks:",
    ]
    for task in payload["tasks"]:
        lines.append(
            f"- {task['task_id']} | {task['category']} | {task['workflow']} | {task['title']}"
        )
        lines.append(f"  objective: {task['objective']}")
        if task["scope_dirs"]:
            lines.append(f"  scope_dirs: {', '.join(task['scope_dirs'])}")
    return "\n".join(lines)


def render_benchmark_run_result(result, output_format: str) -> str:
    payload = {
        "pack_id": result.pack_id,
        "task_id": result.task_id,
        "category": result.category,
        "workflow": result.workflow,
        "model": result.model,
        "status": result.status,
        "scope_dirs": list(result.scope_dirs),
        "prompt_text": result.prompt_text,
        "latency_ms": result.latency_ms,
        "result_payload": result.result_payload,
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"task_id: {payload['task_id']}",
        f"category: {payload['category']}",
        f"workflow: {payload['workflow']}",
        f"model: {payload['model']}",
        f"status: {payload['status']}",
        f"latency_ms: {payload['latency_ms']}",
        "prompt:",
        payload["prompt_text"],
    ]
    result_payload = payload["result_payload"]
    if isinstance(result_payload, dict):
        lines.append("result_keys:")
        for key in result_payload.keys():
            lines.append(f"- {key}")
    return "\n".join(lines)


def render_benchmark_history(entries, output_format: str) -> str:
    payload = [serialize_benchmark_run_history_entry(entry) for entry in entries]
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload:
        return "No saved benchmark run history."

    lines: list[str] = []
    for entry in payload:
        lines.append(
            f"{entry['entry_id']} | {entry['created_at']} | {entry['pack_id']} | "
            f"{entry['task_id']} | {entry['workflow']} | {entry['model']} | {entry['status']}"
        )
    return "\n".join(lines)


def render_benchmark_compare_result(comparison, output_format: str) -> str:
    payload = {
        "pack_id": comparison.pack_id,
        "task_ids": list(comparison.task_ids),
        "entries": [
            {
                "model": entry.model,
                "task_id": entry.task_id,
                "workflow": entry.workflow,
                "status": entry.status,
                "latency_ms": entry.latency_ms,
                "result_payload": entry.result_payload,
            }
            for entry in comparison.entries
        ],
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"pack_id: {payload['pack_id']}",
        f"task_count: {len(payload['task_ids'])}",
        f"entry_count: {len(payload['entries'])}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['task_id']} | {entry['model']} | {entry['workflow']} | "
            f"{entry['status']} | {entry['latency_ms']} ms"
        )
    return "\n".join(lines)


def render_note_change_proposal(proposal, output_format: str) -> str:
    payload = serialize_note_change_proposal(proposal)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"action: {payload['action']}",
        f"target_path: {payload['target_path']}",
        f"title: {payload['title']}",
        f"reason: {payload['reason']}",
    ]
    if payload["similar_notes"]:
        lines.append("similar_notes:")
        for note in payload["similar_notes"]:
            lines.append(f"- {note}")
    if payload["warnings"]:
        lines.append("warnings:")
        for warning in payload["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def render_applied_note_change(proposal, change, output_format: str) -> str:
    payload = {
        "proposal": serialize_note_change_proposal(proposal),
        "change": serialize_applied_note_change(change),
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"action: {payload['change']['action']}",
        f"target_path: {payload['change']['target_path']}",
        f"backup_path: {payload['change']['backup_path']}",
        f"archive_path: {payload['change']['archive_path']}",
    ]
    return "\n".join(lines)


def render_generated_note_draft(draft, output_format: str) -> str:
    payload = serialize_generated_note_draft(draft)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"model: {payload['model']}",
        f"title: {payload['title']}",
        f"action: {payload['proposal']['action']}",
        f"target_path: {payload['proposal']['target_path']}",
        "content:",
        payload["content"],
    ]
    if payload["proposal"]["warnings"]:
        lines.append("warnings:")
        for warning in payload["proposal"]["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def render_generated_note_application(draft, applied, output_format: str) -> str:
    payload = {
        "draft": serialize_generated_note_draft(draft),
        "change": serialize_applied_note_change(applied),
    }
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"model: {payload['draft']['model']}",
        f"title: {payload['draft']['title']}",
        f"target_path: {payload['change']['target_path']}",
        f"backup_path: {payload['change']['backup_path']}",
    ]
    return "\n".join(lines)


def render_maintenance_report(report, output_format: str) -> str:
    payload = serialize_maintenance_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    findings = payload["findings"]
    if not findings:
        return "No maintenance findings."

    lines = [f"generated_at: {payload['generated_at']}", "findings:"]
    for finding in findings:
        lines.append(
            f"- {finding['kind']} | {finding['note']['path']} | {finding['summary']}"
        )
        if finding["proposal"] is not None:
            lines.append(
                f"  proposal: {finding['proposal']['action']} -> {finding['proposal']['target_path']}"
            )
    return "\n".join(lines)


def render_maintenance_plan(plan, output_format: str) -> str:
    payload = serialize_maintenance_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    entries = payload["entries"]
    if not entries:
        return "No actionable maintenance plan entries."

    lines = [f"generated_at: {payload['generated_at']}", "entries:"]
    for entry in entries:
        finding = entry["finding"]
        proposal = entry["proposal"]
        lines.append(
            f"- {finding['note']['path']} | {finding['kind']} | {proposal['action']} -> {proposal['target_path']}"
        )
        if entry["merged_kinds"]:
            lines.append(f"  merged_kinds: {', '.join(entry['merged_kinds'])}")
    if payload["skipped_paths"]:
        lines.append("skipped_paths:")
        for path in payload["skipped_paths"]:
            lines.append(f"- {path}")
    return "\n".join(lines)


def render_maintenance_draft_plan(plan, output_format: str) -> str:
    payload = serialize_maintenance_draft_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    entries = payload["entries"]
    if not entries:
        return "No maintenance draft plan entries."

    lines = [f"generated_at: {payload['generated_at']}", "entries:"]
    for entry in entries:
        finding = entry["plan_entry"]["finding"]
        proposal = entry["draft"]["proposal"]
        lines.append(
            f"- {finding['note']['path']} | {finding['kind']} | draft -> {proposal['target_path']}"
        )
        companion = entry["draft"].get("companion_proposals", [])
        if companion:
            lines.append(f"  companion_proposals: {len(companion)}")
    return "\n".join(lines)


def render_training_corpus(corpus, output_format: str, dataset_format: str) -> str:
    payload = serialize_training_corpus(corpus)
    if dataset_format == "jsonl_chat":
        return render_training_corpus_jsonl(payload["examples"], mode="chat")
    if dataset_format == "jsonl_completion":
        return render_training_corpus_jsonl(payload["examples"], mode="completion")

    if output_format == "json":
        return json.dumps(payload, indent=2)

    examples = payload["examples"]
    if not examples:
        return "No training examples generated."

    lines = [f"generated_at: {payload['generated_at']}", "examples:"]
    for example in examples:
        lines.append(
            f"- {example['example_id']} | {example['task']} | {example['source_note_path']}"
        )
        if example["tags"]:
            lines.append(f"  tags: {', '.join(example['tags'])}")
    return "\n".join(lines)


def render_training_manifest(manifest, output_format: str) -> str:
    payload = serialize_training_manifest(manifest)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_examples: {payload['total_examples']}",
        "by_source:",
    ]
    for key, value in payload["by_source"].items():
        lines.append(f"- {key}: {value}")
    lines.append("by_quality_tier:")
    for key, value in payload["by_quality_tier"].items():
        lines.append(f"- {key}: {value}")
    lines.append("by_task:")
    for key, value in payload["by_task"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def render_training_split(split, output_format: str, dataset_format: str, subset: str) -> str:
    payload = serialize_training_split(split)
    if dataset_format == "jsonl_chat":
        examples = select_split_examples(payload, subset)
        return render_training_corpus_jsonl(examples, mode="chat")
    if dataset_format == "jsonl_completion":
        examples = select_split_examples(payload, subset)
        return render_training_corpus_jsonl(examples, mode="completion")

    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"policy: {payload['policy']}",
        f"train_examples: {len(payload['train_examples'])}",
        f"validation_examples: {len(payload['validation_examples'])}",
    ]
    return "\n".join(lines)


def render_training_fine_tune_bundle(bundle, output_format: str) -> str:
    payload = serialize_training_fine_tune_bundle(bundle)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"bundle_dir: {payload['bundle_dir']}",
        f"train_path: {payload['train_path']}",
        f"validation_path: {payload['validation_path']}",
        f"recipe_path: {payload['recipe_path']}",
        f"runbook_path: {payload['runbook_path']}",
        f"train_examples: {payload['train_examples']}",
        f"validation_examples: {payload['validation_examples']}",
        f"model_family: {payload['recipe']['model_family']}",
        f"recommended_framework: {payload['recipe']['recommended_framework']}",
    ]
    if payload["trainer_artifacts"]:
        lines.append("trainer_artifacts:")
        for artifact in payload["trainer_artifacts"]:
            lines.append(f"- {artifact['trainer']}: {artifact['path']}")
    return "\n".join(lines)


def render_training_evaluation_report(report, output_format: str) -> str:
    payload = serialize_training_evaluation_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"model: {payload['model']}",
        f"subset: {payload['subset']}",
        f"average_score: {payload['average_score']}",
        f"exact_match_rate: {payload['exact_match_rate']}",
        "results:",
    ]
    for result in payload["results"]:
        lines.append(
            f"- {result['example_id']} | score={result['score']} | exact_match={result['exact_match']}"
        )
    if payload["failure_snapshots"]:
        lines.append("failure_snapshots:")
        for snapshot in payload["failure_snapshots"]:
            lines.append(
                f"- {snapshot['example_id']} | score={snapshot['score']} | "
                f"tags={', '.join(snapshot['error_tags']) if snapshot['error_tags'] else 'none'} | "
                f"preview={snapshot['output_markdown_preview']}"
            )
    if payload["prompt_patch_suggestions"]:
        lines.append("prompt_patch_suggestions:")
        for suggestion in payload["prompt_patch_suggestions"]:
            lines.append(
                f"- {suggestion['error_tag']} x{suggestion['occurrences']} | instruction={suggestion['instruction']}"
            )
    return "\n".join(lines)


def render_training_evaluation_leaderboard(leaderboard, output_format: str) -> str:
    payload = serialize_training_evaluation_leaderboard(leaderboard)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload["entries"]:
        return "No saved evaluation history."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_runs: {payload['total_runs']}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['model']} | {entry['subset']} | runs={entry['runs']} | "
            f"latest_score={entry['latest_score']} | average_score={entry['average_score']} | "
            f"delta_vs_previous={entry['delta_vs_previous_score']} | delta_vs_best={entry['delta_vs_best_score']}"
        )
        for snapshot in entry["latest_failure_snapshots"]:
            lines.append(
                f"  failure: {snapshot['example_id']} | score={snapshot['score']} | "
                f"tags={', '.join(snapshot['error_tags']) if snapshot['error_tags'] else 'none'} | "
                f"preview={snapshot['output_markdown_preview']}"
            )
        for suggestion in entry["prompt_patch_suggestions"]:
            lines.append(
                f"  patch: {suggestion['error_tag']} x{suggestion['occurrences']} | instruction={suggestion['instruction']}"
            )
    return "\n".join(lines)


def render_prompt_patch_plan(plan, output_format: str) -> str:
    payload = serialize_prompt_patch_plan(plan)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        "suggestions:",
    ]
    if payload["suggestions"]:
        for suggestion in payload["suggestions"]:
            lines.append(
                f"- {suggestion['error_tag']} x{suggestion['occurrences']} | {suggestion['instruction']}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "optimized_system_prompt:", payload["optimized_system_prompt"]])
    return "\n".join(lines)


def render_training_evaluation_comparison(comparison, output_format: str) -> str:
    payload = serialize_training_evaluation_comparison(comparison)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"model: {payload['model']}",
        f"subset: {payload['subset']}",
        f"score_delta: {payload['score_delta']}",
        f"exact_match_rate_delta: {payload['exact_match_rate_delta']}",
        f"baseline_average_score: {payload['baseline_report']['average_score']}",
        f"optimized_average_score: {payload['optimized_report']['average_score']}",
    ]
    return "\n".join(lines)


def render_training_optimizer_leaderboard(leaderboard, output_format: str) -> str:
    payload = serialize_training_optimizer_leaderboard(leaderboard)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload["entries"]:
        return "No saved optimizer history."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"total_runs: {payload['total_runs']}",
        "entries:",
    ]
    for entry in payload["entries"]:
        lines.append(
            f"- {entry['model']} | {entry['subset']} | runs={entry['runs']} | "
            f"latest_score_delta={entry['latest_score_delta']} | average_score_delta={entry['average_score_delta']}"
        )
    return "\n".join(lines)


def render_training_optimizer_sweep_report(report, output_format: str) -> str:
    payload = serialize_training_optimizer_sweep_report(report)
    if output_format == "json":
        return json.dumps(payload, indent=2)

    if not payload["comparisons"]:
        return "No optimizer sweep comparisons."

    lines = [
        f"generated_at: {payload['generated_at']}",
        f"subset: {payload['subset']}",
        "comparisons:",
    ]
    for comparison in payload["comparisons"]:
        lines.append(
            f"- {comparison['model']} | score_delta={comparison['score_delta']} | "
            f"baseline={comparison['baseline_report']['average_score']} | "
            f"optimized={comparison['optimized_report']['average_score']}"
        )
    return "\n".join(lines)


def render_training_corpus_jsonl(
    examples: list[dict[str, object]],
    *,
    mode: str,
) -> str:
    lines: list[str] = []
    for example in examples:
        if mode == "chat":
            record = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You rewrite Obsidian markdown notes into the vault house style. "
                            "Preserve grounded facts, keep compact structure, use internal [[Note Title]] links, "
                            "and avoid meta commentary."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Task: {example['task']}\n"
                            f"Title: {example['title']}\n"
                            f"Instruction: {example['instruction']}\n\n"
                            "Input note:\n```md\n"
                            f"{example['input_markdown']}```"
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": example["target_markdown"],
                    },
                ],
                "metadata": {
                    "example_id": example["example_id"],
                    "source_note_path": example["source_note_path"],
                    "tags": example["tags"],
                },
            }
        else:
            record = {
                "prompt": (
                    "Rewrite this Obsidian note into the vault house style.\n"
                    f"Task: {example['task']}\n"
                    f"Title: {example['title']}\n"
                    f"Instruction: {example['instruction']}\n\n"
                    "Input note:\n```md\n"
                    f"{example['input_markdown']}```\n\n"
                    "Rewritten note:\n"
                ),
                "completion": example["target_markdown"],
                "metadata": {
                    "example_id": example["example_id"],
                    "source_note_path": example["source_note_path"],
                    "tags": example["tags"],
                },
            }
        lines.append(json.dumps(record, ensure_ascii=True))
    return "\n".join(lines)


def select_split_examples(payload: dict[str, object], subset: str) -> list[dict[str, object]]:
    if subset == "train":
        return list(payload["train_examples"])
    if subset == "validation":
        return list(payload["validation_examples"])
    return [
        *list(payload["train_examples"]),
        *list(payload["validation_examples"]),
    ]

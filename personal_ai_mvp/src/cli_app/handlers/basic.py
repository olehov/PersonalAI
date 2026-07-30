"""Basic scan, retrieval, ask, and history CLI handlers."""

from __future__ import annotations

import argparse

from cli_app.renderers import (
    render_agent_history as _render_agent_history,
    render_agent_runtime_artifact as _render_agent_runtime_artifact,
    render_answer_bundle as _render_answer_bundle,
    render_directory_analysis_report as _render_directory_analysis_report,
    render_generated_answer as _render_generated_answer,
    render_note_detail as _render_note_detail,
    render_note_list as _render_note_list,
    render_query_history as _render_query_history,
    render_retrieval_bundle as _render_retrieval_bundle,
    render_scan as _render_scan,
)
from cli_app.runtime import CliRuntime


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

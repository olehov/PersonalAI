"""Note mutation and drafting CLI handlers."""

from __future__ import annotations

import argparse

from cli_app.renderers import (
    render_applied_note_change as _render_applied_note_change,
    render_generated_note_application as _render_generated_note_application,
    render_generated_note_draft as _render_generated_note_draft,
    render_note_change_proposal as _render_note_change_proposal,
)
from cli_app.runtime import CliRuntime


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

"""Maintenance inspection and drafting CLI handlers."""

from __future__ import annotations

import argparse

from cli_app.renderers import (
    render_generated_note_application as _render_generated_note_application,
    render_generated_note_draft as _render_generated_note_draft,
    render_maintenance_draft_plan as _render_maintenance_draft_plan,
    render_maintenance_plan as _render_maintenance_plan,
    render_maintenance_report as _render_maintenance_report,
)
from cli_app.runtime import CliRuntime


def _find_maintenance_finding(args: argparse.Namespace, runtime: CliRuntime):
    return runtime.maintenance_service.find_finding(args.note, kind=args.kind)


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

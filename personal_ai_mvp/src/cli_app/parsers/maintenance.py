"""Maintenance CLI subparser builders."""

from __future__ import annotations


def add_maintenance_parsers(
    subparsers,
    *,
    default_model: str,
    add_maintenance_draft_arguments,
) -> None:
    """Register maintenance inspection and maintenance-draft subcommands."""
    subparsers.add_parser(
        "maintenance",
        help="Inspect the vault for sparse, isolated, duplicate, or archivable notes.",
    )

    maintenance_plan_parser = subparsers.add_parser(
        "maintenance-plan",
        help="Build a compact batch of compatible maintenance proposals for review.",
    )
    maintenance_plan_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of actionable maintenance entries to include.",
    )
    maintenance_plan_parser.add_argument(
        "--kind",
        action="append",
        default=[],
        choices=("empty_note", "sparse_note", "isolated_note", "duplicate_title"),
        help="Optional maintenance finding kinds to include.",
    )

    maintenance_plan_draft_parser = subparsers.add_parser(
        "maintenance-plan-draft",
        help="Generate drafts for a compact batch of compatible maintenance proposals.",
    )
    maintenance_plan_draft_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of actionable maintenance entries to draft.",
    )
    maintenance_plan_draft_parser.add_argument(
        "--kind",
        action="append",
        default=[],
        choices=("empty_note", "sparse_note", "isolated_note", "duplicate_title"),
        help="Optional maintenance finding kinds to include.",
    )
    maintenance_plan_draft_parser.add_argument(
        "--model",
        default=default_model,
        help="Ollama model name to use.",
    )

    maintenance_draft_parser = subparsers.add_parser(
        "maintenance-draft",
        help="Generate a grounded maintenance refactor draft for an actionable finding.",
    )
    add_maintenance_draft_arguments(maintenance_draft_parser, include_approval=False)

    maintenance_draft_write_parser = subparsers.add_parser(
        "maintenance-draft-write",
        help="Generate and apply a grounded maintenance refactor draft after explicit approval.",
    )
    add_maintenance_draft_arguments(maintenance_draft_write_parser, include_approval=True)

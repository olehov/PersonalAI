"""Note CLI subparser builders."""

from __future__ import annotations


def add_note_parsers(
    subparsers,
    *,
    add_note_mutation_arguments,
    add_note_draft_arguments,
) -> None:
    """Register note proposal/write/draft subcommands."""
    propose_parser = subparsers.add_parser(
        "propose-note",
        help="Prepare a safe note create/update/refactor/archive proposal.",
    )
    add_note_mutation_arguments(propose_parser, include_approval=False)

    write_parser = subparsers.add_parser(
        "write-note",
        help="Apply a safe note mutation after explicit approval.",
    )
    add_note_mutation_arguments(write_parser, include_approval=True)

    draft_parser = subparsers.add_parser(
        "draft-note",
        help="Generate a grounded markdown draft and wrap it in a safe proposal.",
    )
    add_note_draft_arguments(draft_parser, include_approval=False)

    draft_write_parser = subparsers.add_parser(
        "draft-write-note",
        help="Generate a grounded markdown draft and apply it after explicit approval.",
    )
    add_note_draft_arguments(draft_write_parser, include_approval=True)

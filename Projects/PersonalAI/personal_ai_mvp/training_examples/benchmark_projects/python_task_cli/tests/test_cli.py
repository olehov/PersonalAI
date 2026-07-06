from task_cli.cli import build_parser


def test_parser_supports_add_and_list_commands() -> None:
    parser = build_parser()

    add_args = parser.parse_args(["add", "write docs"])
    list_args = parser.parse_args(["list"])

    assert add_args.command == "add"
    assert add_args.title == "write docs"
    assert list_args.command == "list"


def test_done_command_is_not_implemented_yet() -> None:
    parser = build_parser()

    actions = parser._subparsers._group_actions[0]
    command_parser = actions.choices

    assert "done" not in command_parser

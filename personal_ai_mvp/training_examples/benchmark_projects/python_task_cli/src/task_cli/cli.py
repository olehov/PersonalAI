"""Minimal CLI entrypoint for the benchmark project."""

from __future__ import annotations

import argparse
from pathlib import Path

from task_cli.store import TaskStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="task-cli")
    parser.add_argument(
        "--db",
        default="tasks.json",
        help="Path to the JSON task database.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("title")

    subparsers.add_parser("list")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = TaskStore(Path(args.db))

    if args.command == "add":
        task = store.add(args.title)
        print(f"added:{task['id']}:{task['title']}")
        return 0

    if args.command == "list":
        for task in store.list_tasks():
            status = "done" if task["done"] else "todo"
            print(f"{task['id']} {status} {task['title']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

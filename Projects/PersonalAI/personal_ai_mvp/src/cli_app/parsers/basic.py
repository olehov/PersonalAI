"""Basic CLI subparser builders."""

from __future__ import annotations


def add_basic_parsers(
    subparsers,
    *,
    default_model: str,
) -> None:
    """Register scan/retrieval/history-style subcommands."""
    subparsers.add_parser("scan", help="Scan the vault and print a compact summary.")
    subparsers.add_parser("list", help="List indexed notes.")

    analyze_dir_parser = subparsers.add_parser(
        "analyze-dir",
        help="Analyze a whole directory slice, including note graph coverage and gaps.",
    )
    analyze_dir_parser.add_argument("directory", help="Relative vault directory to analyze.")

    search_parser = subparsers.add_parser("search", help="Search notes by title or content.")
    search_parser.add_argument("query", help="Search query.")

    related_parser = subparsers.add_parser("related", help="Show notes linked from a note.")
    related_parser.add_argument("note", help="Note title or relative path.")

    show_parser = subparsers.add_parser("show", help="Show a single note summary.")
    show_parser.add_argument("note", help="Note title or relative path.")

    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="Build a context bundle for a user question.",
    )
    retrieve_parser.add_argument("question", help="User question to ground in vault knowledge.")
    retrieve_parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories.",
    )

    answer_parser = subparsers.add_parser(
        "answer",
        help="Prepare a grounded answer payload for a future LLM.",
    )
    answer_parser.add_argument("question", help="User question to answer with vault grounding.")
    answer_parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories.",
    )

    ask_parser = subparsers.add_parser(
        "ask",
        help="Send a grounded question to a local Ollama model.",
    )
    ask_parser.add_argument("question", help="User question to answer with Ollama.")
    ask_parser.add_argument(
        "--model",
        default=default_model,
        help="Ollama model name to use.",
    )
    ask_parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories.",
    )

    agent_runtime_parser = subparsers.add_parser(
        "agent-runtime",
        help="Run a planning-oriented agent runtime for project-scale coding requests.",
    )
    agent_runtime_parser.add_argument(
        "request_text",
        help="Project-scale request to decompose into grounded implementation slices.",
    )
    agent_runtime_parser.add_argument(
        "--model",
        default=default_model,
        help="Ollama model name to use.",
    )
    agent_runtime_parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories.",
    )

    history_parser = subparsers.add_parser(
        "history",
        help="Show recent persisted grounded ask history from the local SQLite database.",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of history entries to return.",
    )

    agent_history_parser = subparsers.add_parser(
        "agent-history",
        help="Show recent persisted agent runtime history from the local SQLite database.",
    )
    agent_history_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of agent history entries to return.",
    )

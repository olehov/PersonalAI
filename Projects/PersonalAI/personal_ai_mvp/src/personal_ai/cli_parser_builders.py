"""Grouped subparser builders for the PersonalAI CLI."""

from __future__ import annotations

import argparse
from pathlib import Path


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


def add_benchmark_parsers(
    subparsers,
    *,
    default_model: str,
    default_benchmark_pack_path: Path,
) -> None:
    """Register benchmark subcommands."""
    benchmark_pack_parser = subparsers.add_parser(
        "benchmark-pack",
        help="Inspect the repo-aware benchmark pack used for model evaluation.",
    )
    benchmark_pack_parser.add_argument(
        "--pack-file",
        type=Path,
        default=default_benchmark_pack_path,
        help="Path to the benchmark pack JSON file.",
    )
    benchmark_pack_parser.add_argument(
        "--task-id",
        help="Optional benchmark task id filter.",
    )

    benchmark_run_parser = subparsers.add_parser(
        "benchmark-run",
        help="Execute one benchmark-pack task and persist the run artifact.",
    )
    benchmark_run_parser.add_argument(
        "--pack-file",
        type=Path,
        default=default_benchmark_pack_path,
        help="Path to the benchmark pack JSON file.",
    )
    benchmark_run_parser.add_argument(
        "--task-id",
        required=True,
        help="Benchmark task id to execute.",
    )
    benchmark_run_parser.add_argument(
        "--model",
        default=default_model,
        help="Model to use for the benchmark run.",
    )

    benchmark_history_parser = subparsers.add_parser(
        "benchmark-history",
        help="Show recent persisted benchmark run artifacts.",
    )
    benchmark_history_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of benchmark run entries to return.",
    )

    benchmark_compare_parser = subparsers.add_parser(
        "benchmark-compare",
        help="Run one benchmark task or a whole pack across multiple models.",
    )
    benchmark_compare_parser.add_argument(
        "--pack-file",
        type=Path,
        default=default_benchmark_pack_path,
        help="Path to the benchmark pack JSON file.",
    )
    benchmark_compare_parser.add_argument(
        "--task-id",
        help="Optional single benchmark task id to compare. Omit to compare the whole pack.",
    )
    benchmark_compare_parser.add_argument(
        "--model",
        action="append",
        dest="models",
        required=True,
        help="Model to include in the comparison. Pass multiple times for multiple models.",
    )


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


def add_training_parsers(
    subparsers,
    *,
    default_model: str,
    default_eval_history_path: Path,
    default_compare_history_path: Path,
    default_fine_tune_bundles_dir: Path,
) -> None:
    """Register training corpus, eval, and optimizer subcommands."""
    training_corpus_parser = subparsers.add_parser(
        "training-corpus",
        help="Generate supervised training examples from canonical vault notes.",
    )
    training_corpus_parser.add_argument("--limit", type=int, default=50, help="Maximum number of supervised examples to generate.")
    training_corpus_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to export.")
    training_corpus_parser.add_argument("--dataset-format", choices=("corpus_json", "jsonl_chat", "jsonl_completion"), default="corpus_json", help="Export format for training examples.")

    training_manifest_parser = subparsers.add_parser(
        "training-manifest",
        help="Summarize training corpus composition by source, quality, and task.",
    )
    training_manifest_parser.add_argument("--limit", type=int, default=50, help="Maximum number of supervised examples to analyze.")
    training_manifest_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to summarize.")

    training_split_parser = subparsers.add_parser(
        "training-split",
        help="Build a deterministic train/validation split for the training corpus.",
    )
    training_split_parser.add_argument("--limit", type=int, default=50, help="Maximum number of supervised examples to split.")
    training_split_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to split.")
    training_split_parser.add_argument("--validation-ratio", type=float, default=0.2, help="Fraction of examples to place into validation.")
    training_split_parser.add_argument("--dataset-format", choices=("split_json", "jsonl_chat", "jsonl_completion"), default="split_json", help="Export format for the split.")
    training_split_parser.add_argument("--subset", choices=("both", "train", "validation"), default="both", help="Subset to export for JSONL formats.")

    training_bundle_parser = subparsers.add_parser(
        "training-bundle",
        help="Write a train-ready LoRA fine-tuning bundle with JSONL datasets and a recipe.",
    )
    training_bundle_parser.add_argument("--limit", type=int, default=50, help="Maximum number of supervised examples to consider before splitting.")
    training_bundle_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to bundle.")
    training_bundle_parser.add_argument("--validation-ratio", type=float, default=0.2, help="Fraction of examples to place into validation.")
    training_bundle_parser.add_argument("--model-family", choices=("generic", "llama", "qwen", "mistral"), default="generic", help="Target model family for recipe recommendations.")
    training_bundle_parser.add_argument("--output-dir", type=Path, default=default_fine_tune_bundles_dir, help="Directory where the fine-tuning bundle should be written.")

    training_eval_parser = subparsers.add_parser(
        "training-eval",
        help="Run a simple model evaluation over the training split.",
    )
    training_eval_parser.add_argument("--limit", type=int, default=20, help="Maximum number of supervised examples to consider before splitting.")
    training_eval_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to evaluate.")
    training_eval_parser.add_argument("--validation-ratio", type=float, default=0.2, help="Fraction of examples to place into validation.")
    training_eval_parser.add_argument("--subset", choices=("train", "validation"), default="validation", help="Which split subset to evaluate.")
    training_eval_parser.add_argument("--model", default=default_model, help="Ollama model name to evaluate.")
    training_eval_parser.add_argument("--history-file", type=Path, default=default_eval_history_path, help="JSONL file used to append evaluation history.")
    training_eval_parser.add_argument("--apply-history-patches", action="store_true", help="Augment the evaluation system prompt with patch suggestions from saved history.")
    training_eval_parser.add_argument("--patch-limit", type=int, default=5, help="Maximum number of prompt patch suggestions to apply.")

    training_eval_compare_parser = subparsers.add_parser(
        "training-eval-compare",
        help="Run baseline and optimized eval side by side and report the delta.",
    )
    training_eval_compare_parser.add_argument("--limit", type=int, default=20, help="Maximum number of supervised examples to consider before splitting.")
    training_eval_compare_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to evaluate.")
    training_eval_compare_parser.add_argument("--validation-ratio", type=float, default=0.2, help="Fraction of examples to place into validation.")
    training_eval_compare_parser.add_argument("--subset", choices=("train", "validation"), default="validation", help="Which split subset to evaluate.")
    training_eval_compare_parser.add_argument("--model", default=default_model, help="Ollama model name to evaluate.")
    training_eval_compare_parser.add_argument("--history-file", type=Path, default=default_eval_history_path, help="JSONL file containing saved evaluation history.")
    training_eval_compare_parser.add_argument("--patch-limit", type=int, default=5, help="Maximum number of prompt patch suggestions to apply.")
    training_eval_compare_parser.add_argument("--compare-history-file", type=Path, default=default_compare_history_path, help="JSONL file used to append comparison history.")

    training_leaderboard_parser = subparsers.add_parser(
        "training-leaderboard",
        help="Summarize saved evaluation history into a per-model leaderboard.",
    )
    training_leaderboard_parser.add_argument("--history-file", type=Path, default=default_eval_history_path, help="JSONL file containing saved evaluation history.")
    training_leaderboard_parser.add_argument("--subset", choices=("train", "validation"), help="Optional subset filter for leaderboard aggregation.")

    training_prompt_parser = subparsers.add_parser(
        "training-prompt-patches",
        help="Build an optimized eval system prompt from saved failure taxonomy.",
    )
    training_prompt_parser.add_argument("--history-file", type=Path, default=default_eval_history_path, help="JSONL file containing saved evaluation history.")
    training_prompt_parser.add_argument("--subset", choices=("train", "validation"), help="Optional subset filter for prompt patch aggregation.")
    training_prompt_parser.add_argument("--model", help="Optional model filter for prompt patch aggregation.")
    training_prompt_parser.add_argument("--limit", type=int, default=5, help="Maximum number of aggregated patch suggestions to include.")

    training_optimizer_parser = subparsers.add_parser(
        "training-optimizer-leaderboard",
        help="Summarize saved compare runs into an optimizer leaderboard.",
    )
    training_optimizer_parser.add_argument("--compare-history-file", type=Path, default=default_compare_history_path, help="JSONL file containing saved comparison history.")
    training_optimizer_parser.add_argument("--subset", choices=("train", "validation"), help="Optional subset filter for optimizer aggregation.")
    training_optimizer_parser.add_argument("--model", help="Optional model filter for optimizer aggregation.")

    training_optimizer_sweep_parser = subparsers.add_parser(
        "training-optimizer-sweep",
        help="Run optimizer compare loops across multiple models.",
    )
    training_optimizer_sweep_parser.add_argument("--limit", type=int, default=20, help="Maximum number of supervised examples to consider before splitting.")
    training_optimizer_sweep_parser.add_argument("--source", choices=("all", "curated", "synthetic", "ukrainian"), default="all", help="Which example source to evaluate.")
    training_optimizer_sweep_parser.add_argument("--validation-ratio", type=float, default=0.2, help="Fraction of examples to place into validation.")
    training_optimizer_sweep_parser.add_argument("--subset", choices=("train", "validation"), default="validation", help="Which split subset to evaluate.")
    training_optimizer_sweep_parser.add_argument("--model", action="append", required=True, help="Model name to include. Repeat the flag for multiple models.")
    training_optimizer_sweep_parser.add_argument("--history-file", type=Path, default=default_eval_history_path, help="JSONL file containing saved evaluation history.")
    training_optimizer_sweep_parser.add_argument("--compare-history-file", type=Path, default=default_compare_history_path, help="JSONL file used to append comparison history.")
    training_optimizer_sweep_parser.add_argument("--patch-limit", type=int, default=5, help="Maximum number of prompt patch suggestions to apply.")

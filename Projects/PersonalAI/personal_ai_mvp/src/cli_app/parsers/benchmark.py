"""Benchmark CLI subparser builders."""

from __future__ import annotations

from pathlib import Path


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

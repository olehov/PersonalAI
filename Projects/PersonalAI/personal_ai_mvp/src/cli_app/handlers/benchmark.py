"""Benchmark CLI handlers."""

from __future__ import annotations

import argparse

from cli_app.renderers import (
    render_benchmark_compare_result as _render_benchmark_compare_result,
    render_benchmark_history as _render_benchmark_history,
    render_benchmark_pack as _render_benchmark_pack,
    render_benchmark_run_result as _render_benchmark_run_result,
)
from cli_app.runtime import CliRuntime


def handle_benchmark_command(args: argparse.Namespace, runtime: CliRuntime) -> int | None:
    """Handle benchmark pack/run/history/compare commands."""
    if args.command == "benchmark-pack":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        print(_render_benchmark_pack(pack, args.format, task_id=args.task_id))
        return 0
    if args.command == "benchmark-run":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        task = next((item for item in pack.tasks if item.task_id == args.task_id), None)
        if task is None:
            print(f"Benchmark task not found: {args.task_id}")
            return 1
        result = runtime.benchmark_run_service.run_task(
            pack_id=pack.pack_id,
            task=task,
            model=args.model,
        )
        print(_render_benchmark_run_result(result, args.format))
        return 0
    if args.command == "benchmark-history":
        entries = runtime.history_repository.list_benchmark_runs(limit=args.limit)
        print(_render_benchmark_history(entries, args.format))
        return 0
    if args.command == "benchmark-compare":
        pack = runtime.benchmark_pack_service.load_pack(args.pack_file)
        if args.task_id:
            tasks = tuple(item for item in pack.tasks if item.task_id == args.task_id)
            if not tasks:
                print(f"Benchmark task not found: {args.task_id}")
                return 1
        else:
            tasks = pack.tasks
        comparison = runtime.benchmark_run_service.compare_models(
            pack_id=pack.pack_id,
            tasks=tasks,
            models=tuple(args.models),
        )
        print(_render_benchmark_compare_result(comparison, args.format))
        return 0
    return None

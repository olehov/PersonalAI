"""Compare a base local model and a local fine-tuned adapter on one training subset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from application.knowledge_service import KnowledgeService
from application.training_corpus_service import TrainingCorpusService
from application.training_eval_service import TrainingEvalService
from infrastructure.llm.ollama_client import OllamaClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare a base local model and a local adapter on a selected training subset.",
    )
    parser.add_argument("--vault", type=Path, required=True, help="Path to the vault root.")
    parser.add_argument(
        "--source",
        default="ukrainian",
        choices=("all", "curated", "synthetic", "ukrainian"),
        help="Training corpus source to evaluate.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of examples to consider before splitting.",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.2,
        help="Fraction of examples to place into validation.",
    )
    parser.add_argument(
        "--subset",
        choices=("train", "validation"),
        default="validation",
        help="Which split subset to evaluate.",
    )
    parser.add_argument(
        "--base-model",
        required=True,
        help="Base local model path or name.",
    )
    parser.add_argument(
        "--adapter-model",
        required=True,
        help="Adapter/local model path to compare against the base model.",
    )
    parser.add_argument(
        "--base-label",
        default="base-local",
        help="Display label for the base model in the comparison payload.",
    )
    parser.add_argument(
        "--adapter-label",
        default="adapter-local",
        help="Display label for the adapter model in the comparison payload.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Where to write the comparison JSON payload.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        help="Optional markdown report path. Defaults to the JSON output path with a .md suffix.",
    )
    return parser


def _build_markdown_report(
    *,
    payload: dict[str, object],
) -> str:
    base = payload["base"]
    adapter = payload["adapter"]
    deltas = payload["deltas"]

    base_results = {
        result["example_id"]: result
        for result in base["results"]
    }
    adapter_results = {
        result["example_id"]: result
        for result in adapter["results"]
    }
    common_ids = [
        example_id
        for example_id in base_results
        if example_id in adapter_results
    ]

    lines = [
        "# Ukrainian Evaluation Comparison",
        "",
        f"- Source: `{payload['source']}`",
        f"- Subset: `{payload['subset']}`",
        f"- Example count: `{payload['example_count']}`",
        f"- Base model: `{base['model']}`",
        f"- Adapter model: `{adapter['model']}`",
        "",
        "## Summary",
        "",
        "| Metric | Base | Adapter | Delta |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Average score | {base['average_score']:.3f} | "
            f"{adapter['average_score']:.3f} | {deltas['average_score']:+.3f} |"
        ),
        (
            f"| Exact match rate | {base['exact_match_rate']:.3f} | "
            f"{adapter['exact_match_rate']:.3f} | {deltas['exact_match_rate']:+.3f} |"
        ),
        "",
        "## Per-Example Scores",
        "",
        "| Example | Base | Adapter | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]

    for example_id in common_ids:
        base_result = base_results[example_id]
        adapter_result = adapter_results[example_id]
        delta = adapter_result["score"] - base_result["score"]
        lines.append(
            f"| `{example_id}` | {base_result['score']:.3f} | "
            f"{adapter_result['score']:.3f} | {delta:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Sample Outputs",
            "",
        ]
    )

    for example_id in common_ids:
        base_result = base_results[example_id]
        adapter_result = adapter_results[example_id]
        lines.extend(
            [
                f"### `{example_id}`",
                "",
                f"- Base score: `{base_result['score']:.3f}`",
                f"- Adapter score: `{adapter_result['score']:.3f}`",
                "",
                "#### Base Output",
                "",
                str(base_result["output_markdown"]).rstrip(),
                "",
                "#### Adapter Output",
                "",
                str(adapter_result["output_markdown"]).rstrip(),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    knowledge = KnowledgeService(args.vault)
    knowledge.load()
    split = TrainingCorpusService(knowledge).build_split(
        limit=args.limit,
        source=args.source,
        validation_ratio=args.validation_ratio,
    )
    examples = split.validation_examples if args.subset == "validation" else split.train_examples

    service = TrainingEvalService(
        OllamaClient(base_url="http://127.0.0.1:11435", timeout_seconds=1800)
    )
    base = service.evaluate_local_model(
        model_path_or_name=args.base_model,
        model_label=args.base_label,
        examples=examples,
        subset=args.subset,
    )
    adapter = service.evaluate_local_model(
        model_path_or_name=args.adapter_model,
        model_label=args.adapter_label,
        examples=examples,
        subset=args.subset,
    )

    payload = {
        "subset": args.subset,
        "source": args.source,
        "example_count": len(examples),
        "base": {
            "model": base.model,
            "average_score": base.average_score,
            "exact_match_rate": base.exact_match_rate,
            "failure_snapshots": [
                {
                    "example_id": snapshot.example_id,
                    "score": snapshot.score,
                    "error_tags": list(snapshot.error_tags),
                    "preview": snapshot.output_markdown_preview,
                }
                for snapshot in base.failure_snapshots
            ],
            "results": [
                {
                    "example_id": result.example_id,
                    "score": result.score,
                    "exact_match": result.exact_match,
                    "output_markdown": result.output_markdown,
                }
                for result in base.results
            ],
        },
        "adapter": {
            "model": adapter.model,
            "average_score": adapter.average_score,
            "exact_match_rate": adapter.exact_match_rate,
            "failure_snapshots": [
                {
                    "example_id": snapshot.example_id,
                    "score": snapshot.score,
                    "error_tags": list(snapshot.error_tags),
                    "preview": snapshot.output_markdown_preview,
                }
                for snapshot in adapter.failure_snapshots
            ],
            "results": [
                {
                    "example_id": result.example_id,
                    "score": result.score,
                    "exact_match": result.exact_match,
                    "output_markdown": result.output_markdown,
                }
                for result in adapter.results
            ],
        },
        "deltas": {
            "average_score": round(adapter.average_score - base.average_score, 4),
            "exact_match_rate": round(adapter.exact_match_rate - base.exact_match_rate, 4),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )
    report_output = args.report_output or args.output.with_suffix(".md")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        _build_markdown_report(payload=payload),
        encoding="utf-8-sig",
    )
    print(
        json.dumps(
            {
                "saved_to": str(args.output),
                "report_saved_to": str(report_output),
                "base_average_score": base.average_score,
                "adapter_average_score": adapter.average_score,
                "delta": round(adapter.average_score - base.average_score, 4),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

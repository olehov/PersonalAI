"""Training CLI subparser builders."""

from __future__ import annotations

from pathlib import Path


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

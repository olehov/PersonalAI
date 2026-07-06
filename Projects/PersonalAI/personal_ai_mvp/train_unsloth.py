"""Minimal local Unsloth training entrypoint for generated fine-tune bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a LoRA adapter with Unsloth from bundle JSONL files.",
    )
    parser.add_argument("--config", type=Path, help="Optional Unsloth JSON config file.")
    parser.add_argument("--model-name", help="Base model to load.")
    parser.add_argument("--train-file", type=Path, help="Training JSONL file.")
    parser.add_argument("--validation-file", type=Path, help="Validation JSONL file.")
    parser.add_argument("--output-dir", type=Path, help="Output directory for adapter checkpoints.")
    parser.add_argument("--max-seq-length", type=int, help="Maximum sequence length.")
    parser.add_argument("--learning-rate", type=float, help="Learning rate.")
    parser.add_argument("--num-epochs", type=int, help="Number of training epochs.")
    parser.add_argument("--micro-batch-size", type=int, help="Per-device train batch size.")
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        help="Gradient accumulation steps.",
    )
    parser.add_argument("--lora-r", type=int, help="LoRA rank.")
    parser.add_argument("--lora-alpha", type=int, help="LoRA alpha.")
    parser.add_argument("--lora-dropout", type=float, help="LoRA dropout.")
    parser.add_argument(
        "--load-in-4bit",
        action="store_true",
        help="Load the base model in 4-bit mode.",
    )
    parser.add_argument(
        "--logging-steps",
        type=int,
        default=5,
        help="Trainer logging interval.",
    )
    parser.add_argument(
        "--save-strategy",
        default="epoch",
        help="Checkpoint save strategy.",
    )
    parser.add_argument(
        "--eval-strategy",
        default="epoch",
        help="Evaluation strategy when a validation file is present.",
    )
    parser.add_argument(
        "--max-train-samples",
        type=int,
        help="Optional limit for quick smoke runs.",
    )
    parser.add_argument(
        "--max-eval-samples",
        type=int,
        help="Optional limit for quick smoke runs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load config and dataset metadata without starting training.",
    )
    return parser.parse_args()


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    settings = {
        "model_name": None,
        "train_file": None,
        "validation_file": None,
        "output_dir": None,
        "max_seq_length": config.get("max_seq_length", 4096),
        "learning_rate": config.get("learning_rate", 2e-4),
        "num_train_epochs": config.get("num_train_epochs", 3),
        "per_device_train_batch_size": config.get("per_device_train_batch_size", 2),
        "gradient_accumulation_steps": config.get("gradient_accumulation_steps", 8),
        "lora_r": config.get("lora_r", 16),
        "lora_alpha": config.get("lora_alpha", 32),
        "lora_dropout": config.get("lora_dropout", 0.05),
        "load_in_4bit": config.get("load_in_4bit", False),
        "logging_steps": args.logging_steps,
        "save_strategy": args.save_strategy,
        "eval_strategy": args.eval_strategy,
        "max_train_samples": args.max_train_samples,
        "max_eval_samples": args.max_eval_samples,
        "dry_run": args.dry_run,
    }

    if args.model_name is not None:
        settings["model_name"] = args.model_name
    if args.train_file is not None:
        settings["train_file"] = args.train_file
    if args.validation_file is not None:
        settings["validation_file"] = args.validation_file
    if args.output_dir is not None:
        settings["output_dir"] = args.output_dir
    if args.max_seq_length is not None:
        settings["max_seq_length"] = args.max_seq_length
    if args.learning_rate is not None:
        settings["learning_rate"] = args.learning_rate
    if args.num_epochs is not None:
        settings["num_train_epochs"] = args.num_epochs
    if args.micro_batch_size is not None:
        settings["per_device_train_batch_size"] = args.micro_batch_size
    if args.gradient_accumulation_steps is not None:
        settings["gradient_accumulation_steps"] = args.gradient_accumulation_steps
    if args.lora_r is not None:
        settings["lora_r"] = args.lora_r
    if args.lora_alpha is not None:
        settings["lora_alpha"] = args.lora_alpha
    if args.lora_dropout is not None:
        settings["lora_dropout"] = args.lora_dropout
    if args.load_in_4bit:
        settings["load_in_4bit"] = True

    config_model_name = config.get("model_name")
    if settings["model_name"] is None and config_model_name is not None:
        settings["model_name"] = config_model_name

    if settings["train_file"] is None and config.get("train_file") is not None:
        settings["train_file"] = Path(config["train_file"])
    if settings["validation_file"] is None and config.get("validation_file") is not None:
        settings["validation_file"] = Path(config["validation_file"])
    if settings["output_dir"] is None and config.get("output_dir") is not None:
        settings["output_dir"] = Path(config["output_dir"])

    if settings["train_file"] is None:
        raise ValueError("--train-file or config.train_file is required.")
    if settings["output_dir"] is None:
        raise ValueError("--output-dir or config.output_dir is required.")
    if not settings["model_name"]:
        raise ValueError("--model-name is required.")

    return settings


def _load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        records.append(json.loads(line))
        if limit is not None and len(records) >= limit:
            break
    return records


def _render_chat_record(tokenizer: Any, record: dict[str, Any]) -> str:
    messages = record["messages"]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    return "\n\n".join(
        f"{message['role'].upper()}:\n{message['content']}" for message in messages
    )


def _build_dataset(records: list[dict[str, Any]], tokenizer: Any, max_seq_length: int) -> Any:
    from datasets import Dataset

    rendered = [{"text": _render_chat_record(tokenizer, record)} for record in records]
    dataset = Dataset.from_list(rendered)

    def _tokenize(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        tokens = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )
        tokens["labels"] = [list(ids) for ids in tokens["input_ids"]]
        return tokens

    return dataset.map(
        _tokenize,
        batched=True,
        remove_columns=["text"],
    )


def _print_summary(settings: dict[str, Any], train_records: list[dict[str, Any]], eval_records: list[dict[str, Any]]) -> None:
    summary = {
        "model_name": settings["model_name"],
        "train_file": str(settings["train_file"]),
        "validation_file": str(settings["validation_file"]) if settings["validation_file"] else None,
        "output_dir": str(settings["output_dir"]),
        "max_seq_length": settings["max_seq_length"],
        "learning_rate": settings["learning_rate"],
        "num_train_epochs": settings["num_train_epochs"],
        "per_device_train_batch_size": settings["per_device_train_batch_size"],
        "gradient_accumulation_steps": settings["gradient_accumulation_steps"],
        "lora_r": settings["lora_r"],
        "lora_alpha": settings["lora_alpha"],
        "lora_dropout": settings["lora_dropout"],
        "load_in_4bit": settings["load_in_4bit"],
        "train_examples": len(train_records),
        "validation_examples": len(eval_records),
        "dry_run": settings["dry_run"],
    }
    print(json.dumps(summary, indent=2))


def main() -> int:
    args = _parse_args()
    config = _load_config(args.config)
    settings = _resolve_settings(args, config)

    train_records = _load_jsonl(settings["train_file"], settings["max_train_samples"])
    eval_records = (
        _load_jsonl(settings["validation_file"], settings["max_eval_samples"])
        if settings["validation_file"] is not None and settings["validation_file"].exists()
        else []
    )
    _print_summary(settings, train_records, eval_records)

    if settings["dry_run"]:
        return 0

    from unsloth import FastLanguageModel, UnslothTrainer, UnslothTrainingArguments, is_bfloat16_supported
    from transformers import DataCollatorForSeq2Seq

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=settings["model_name"],
        max_seq_length=settings["max_seq_length"],
        load_in_4bit=settings["load_in_4bit"],
    )
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    model = FastLanguageModel.get_peft_model(
        model,
        r=settings["lora_r"],
        lora_alpha=settings["lora_alpha"],
        lora_dropout=settings["lora_dropout"],
        max_seq_length=settings["max_seq_length"],
    )

    train_dataset = _build_dataset(train_records, tokenizer, settings["max_seq_length"])
    eval_dataset = (
        _build_dataset(eval_records, tokenizer, settings["max_seq_length"])
        if eval_records
        else None
    )

    settings["output_dir"].mkdir(parents=True, exist_ok=True)
    bf16 = bool(is_bfloat16_supported())
    training_args = UnslothTrainingArguments(
        output_dir=str(settings["output_dir"]),
        learning_rate=settings["learning_rate"],
        per_device_train_batch_size=settings["per_device_train_batch_size"],
        gradient_accumulation_steps=settings["gradient_accumulation_steps"],
        num_train_epochs=settings["num_train_epochs"],
        logging_steps=settings["logging_steps"],
        save_strategy=settings["save_strategy"],
        eval_strategy=settings["eval_strategy"] if eval_dataset is not None else "no",
        report_to="none",
        bf16=bf16,
        fp16=not bf16,
        remove_unused_columns=False,
    )
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        label_pad_token_id=-100,
        return_tensors="pt",
    )

    trainer = UnslothTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
    )

    result = trainer.train()
    trainer.save_model(str(settings["output_dir"]))
    tokenizer.save_pretrained(str(settings["output_dir"]))

    metrics_path = settings["output_dir"] / "train_metrics.json"
    metrics = getattr(result, "metrics", {})
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"saved_to": str(settings["output_dir"]), "metrics_file": str(metrics_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

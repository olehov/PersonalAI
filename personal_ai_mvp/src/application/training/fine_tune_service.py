"""Builds train-ready fine-tuning bundles from the supervised corpus."""

from __future__ import annotations

import json
from pathlib import Path

from application.training.corpus_service import TrainingCorpusService
from domain.models import (
    TrainingExample,
    TrainingFineTuneBundle,
    TrainingFineTuneRecipe,
    TrainingTrainerArtifact,
)


class TrainingFineTuneService:
    """Creates persisted LoRA-style training bundles from curated/synthetic examples."""

    def __init__(self, training_corpus_service: TrainingCorpusService) -> None:
        self._training_corpus_service = training_corpus_service

    def build_bundle(
        self,
        *,
        output_dir: Path,
        limit: int = 50,
        source: str = "all",
        validation_ratio: float = 0.2,
        model_family: str = "generic",
    ) -> TrainingFineTuneBundle:
        """Builds a persisted fine-tuning bundle with JSONL datasets and a recipe."""
        split = self._training_corpus_service.build_split(
            limit=limit,
            source=source,
            validation_ratio=validation_ratio,
        )
        recipe = _build_recipe(model_family)
        bundle_dir = output_dir / f"{model_family}_{source}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        train_path = bundle_dir / "train.jsonl"
        validation_path = bundle_dir / "validation.jsonl"
        manifest_path = bundle_dir / "manifest.json"
        recipe_path = bundle_dir / "recipe.json"
        runbook_path = bundle_dir / "RUNBOOK.md"
        unsloth_config_path = bundle_dir / "unsloth_config.json"
        llamafactory_config_path = bundle_dir / "llamafactory_config.json"
        unsloth_launch_ps1_path = bundle_dir / "launch_unsloth.ps1"
        llamafactory_launch_ps1_path = bundle_dir / "launch_llamafactory.ps1"

        train_path.write_text(
            _render_training_jsonl(split.train_examples),
            encoding="utf-8",
        )
        validation_path.write_text(
            _render_training_jsonl(split.validation_examples),
            encoding="utf-8",
        )

        trainer_artifacts = (
            TrainingTrainerArtifact(
                trainer="unsloth",
                kind="config",
                path=unsloth_config_path,
                format="json",
            ),
            TrainingTrainerArtifact(
                trainer="llamafactory",
                kind="config",
                path=llamafactory_config_path,
                format="json",
            ),
            TrainingTrainerArtifact(
                trainer="unsloth",
                kind="launch_script",
                path=unsloth_launch_ps1_path,
                format="powershell",
            ),
            TrainingTrainerArtifact(
                trainer="llamafactory",
                kind="launch_script",
                path=llamafactory_launch_ps1_path,
                format="powershell",
            ),
        )
        bundle = TrainingFineTuneBundle(
            bundle_dir=bundle_dir,
            train_path=train_path,
            validation_path=validation_path,
            manifest_path=manifest_path,
            recipe_path=recipe_path,
            runbook_path=runbook_path,
            trainer_artifacts=trainer_artifacts,
            source=source,
            validation_ratio=validation_ratio,
            train_examples=len(split.train_examples),
            validation_examples=len(split.validation_examples),
            recipe=recipe,
        )
        manifest_path.write_text(
            json.dumps(_serialize_bundle_manifest(bundle, split.policy), indent=2),
            encoding="utf-8",
        )
        recipe_path.write_text(
            json.dumps(_serialize_recipe(recipe), indent=2),
            encoding="utf-8",
        )
        unsloth_config_path.write_text(
            json.dumps(_render_unsloth_config(bundle), indent=2),
            encoding="utf-8",
        )
        llamafactory_config_path.write_text(
            json.dumps(_render_llamafactory_config(bundle), indent=2),
            encoding="utf-8",
        )
        unsloth_launch_ps1_path.write_text(
            _render_unsloth_launch_script(bundle),
            encoding="utf-8",
        )
        llamafactory_launch_ps1_path.write_text(
            _render_llamafactory_launch_script(bundle),
            encoding="utf-8",
        )
        runbook_path.write_text(
            _render_runbook(bundle, split.policy),
            encoding="utf-8",
        )
        return bundle


def _build_recipe(model_family: str) -> TrainingFineTuneRecipe:
    family = model_family.casefold()
    learning_rate = 2e-4
    max_sequence_length = 4096
    notes = [
        "Start with LoRA/QLoRA rather than full-parameter fine-tuning.",
        "Use the curated validation split as the first acceptance gate before wider rollout.",
        "Prefer one short dry run first to confirm tokenization, loss, and checkpoint writing.",
    ]

    if family == "mistral":
        learning_rate = 1.5e-4
        notes.append(
            "Mistral-family models in this repo respond well to structure-preserving rewrite guidance."
        )
    elif family == "qwen":
        learning_rate = 1.5e-4
        notes.append(
            "Qwen-family models benefit from aggressive preservation of exact Obsidian link syntax."
        )
    elif family == "llama":
        learning_rate = 2e-4
        notes.append(
            "Llama-family models here improve strongly when heading hierarchy and no-preface behavior are reinforced."
        )

    return TrainingFineTuneRecipe(
        model_family=model_family,
        dataset_format="jsonl_chat",
        recommended_framework="lora",
        learning_rate=learning_rate,
        num_epochs=3,
        micro_batch_size=2,
        gradient_accumulation_steps=8,
        lora_rank=16,
        lora_alpha=32,
        lora_dropout=0.05,
        max_sequence_length=max_sequence_length,
        notes=tuple(notes),
    )


def _render_training_jsonl(examples: tuple[TrainingExample, ...]) -> str:
    lines: list[str] = []
    for example in examples:
        record = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You rewrite Obsidian markdown notes into the vault house style. "
                        "Preserve grounded facts, keep compact structure, use internal [[Note Title]] links, "
                        "and avoid meta commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Task: {example.task}\n"
                        f"Title: {example.title}\n"
                        f"Instruction: {example.instruction}\n\n"
                        "Input note:\n```md\n"
                        f"{example.input_markdown}```"
                    ),
                },
                {
                    "role": "assistant",
                    "content": example.target_markdown,
                },
            ],
            "metadata": {
                "example_id": example.example_id,
                "source_note_path": example.source_note_path.as_posix(),
                "source": example.source,
                "quality_tier": example.quality_tier,
                "tags": list(example.tags),
            },
        }
        lines.append(json.dumps(record, ensure_ascii=True))
    return "\n".join(lines)


def _serialize_recipe(recipe: TrainingFineTuneRecipe) -> dict[str, object]:
    return {
        "model_family": recipe.model_family,
        "dataset_format": recipe.dataset_format,
        "recommended_framework": recipe.recommended_framework,
        "learning_rate": recipe.learning_rate,
        "num_epochs": recipe.num_epochs,
        "micro_batch_size": recipe.micro_batch_size,
        "gradient_accumulation_steps": recipe.gradient_accumulation_steps,
        "lora_rank": recipe.lora_rank,
        "lora_alpha": recipe.lora_alpha,
        "lora_dropout": recipe.lora_dropout,
        "max_sequence_length": recipe.max_sequence_length,
        "notes": list(recipe.notes),
    }


def _serialize_bundle_manifest(
    bundle: TrainingFineTuneBundle,
    split_policy: str,
) -> dict[str, object]:
    return {
        "generated_at": bundle.generated_at.isoformat(),
        "bundle_dir": bundle.bundle_dir.as_posix(),
        "source": bundle.source,
        "validation_ratio": bundle.validation_ratio,
        "train_examples": bundle.train_examples,
        "validation_examples": bundle.validation_examples,
        "split_policy": split_policy,
        "files": {
            "train": bundle.train_path.name,
            "validation": bundle.validation_path.name,
            "recipe": bundle.recipe_path.name,
            "runbook": bundle.runbook_path.name,
            "trainer_artifacts": {
                f"{artifact.trainer}:{artifact.kind}": artifact.path.name
                for artifact in bundle.trainer_artifacts
            },
        },
        "recipe": _serialize_recipe(bundle.recipe),
    }


def _render_unsloth_config(bundle: TrainingFineTuneBundle) -> dict[str, object]:
    recipe = bundle.recipe
    return {
        "trainer": "unsloth",
        "dataset_format": recipe.dataset_format,
        "train_file": bundle.train_path.as_posix(),
        "validation_file": bundle.validation_path.as_posix(),
        "max_seq_length": recipe.max_sequence_length,
        "learning_rate": recipe.learning_rate,
        "num_train_epochs": recipe.num_epochs,
        "per_device_train_batch_size": recipe.micro_batch_size,
        "gradient_accumulation_steps": recipe.gradient_accumulation_steps,
        "lora_r": recipe.lora_rank,
        "lora_alpha": recipe.lora_alpha,
        "lora_dropout": recipe.lora_dropout,
        "evaluation_strategy": "epoch",
        "load_in_4bit": True,
        "packing": False,
    }


def _render_llamafactory_config(bundle: TrainingFineTuneBundle) -> dict[str, object]:
    recipe = bundle.recipe
    return {
        "trainer": "llamafactory",
        "stage": "sft",
        "dataset_format": recipe.dataset_format,
        "train_file": bundle.train_path.as_posix(),
        "eval_file": bundle.validation_path.as_posix(),
        "cutoff_len": recipe.max_sequence_length,
        "learning_rate": recipe.learning_rate,
        "num_train_epochs": recipe.num_epochs,
        "per_device_train_batch_size": recipe.micro_batch_size,
        "gradient_accumulation_steps": recipe.gradient_accumulation_steps,
        "finetuning_type": "lora",
        "lora_rank": recipe.lora_rank,
        "lora_alpha": recipe.lora_alpha,
        "lora_dropout": recipe.lora_dropout,
        "val_size": 0.0,
        "packing": False,
    }


def _render_runbook(bundle: TrainingFineTuneBundle, split_policy: str) -> str:
    recipe = bundle.recipe
    return "\n".join(
        [
            "# Fine-Tune Runbook",
            "",
            "## Bundle",
            f"- source: `{bundle.source}`",
            f"- train examples: `{bundle.train_examples}`",
            f"- validation examples: `{bundle.validation_examples}`",
            f"- split policy: `{split_policy}`",
            "",
            "## Files",
            f"- train: `{bundle.train_path.name}`",
            f"- validation: `{bundle.validation_path.name}`",
            f"- recipe: `{bundle.recipe_path.name}`",
            *[
                f"- {artifact.trainer} {artifact.kind}: `{artifact.path.name}`"
                for artifact in bundle.trainer_artifacts
            ],
            "",
            "## Recommended Recipe",
            f"- model family: `{recipe.model_family}`",
            f"- framework: `{recipe.recommended_framework}`",
            f"- dataset format: `{recipe.dataset_format}`",
            f"- learning rate: `{recipe.learning_rate}`",
            f"- epochs: `{recipe.num_epochs}`",
            f"- micro batch size: `{recipe.micro_batch_size}`",
            f"- gradient accumulation steps: `{recipe.gradient_accumulation_steps}`",
            f"- LoRA rank: `{recipe.lora_rank}`",
            f"- LoRA alpha: `{recipe.lora_alpha}`",
            f"- LoRA dropout: `{recipe.lora_dropout}`",
            f"- max sequence length: `{recipe.max_sequence_length}`",
            "",
            "## Workflow",
            "1. Start with a short LoRA dry run on the generated train split.",
            "2. Confirm loss decreases and checkpoints are written correctly.",
            "3. Evaluate the resulting adapter on the validation split before merging it into normal note-writing flows.",
            "4. Keep prompt-optimizer evaluation in place even after fine-tuning so regressions remain visible.",
            "5. Start from one of the generated trainer configs instead of rebuilding hyperparameters by hand.",
            "6. The generated Unsloth launch script targets the local .venv-unsloth environment and train_unsloth.py entrypoint.",
            "7. Override BASE_MODEL and OUTPUT_DIR in PowerShell if you want a different model or output location.",
            "",
            "## Notes",
            *[f"- {note}" for note in recipe.notes],
        ]
    ) + "\n"


def _render_unsloth_launch_script(bundle: TrainingFineTuneBundle) -> str:
    recipe = bundle.recipe
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path",
            "$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir '..\\..\\..')).Path",
            "$PythonExe = Join-Path $ProjectRoot '.venv-unsloth\\Scripts\\python.exe'",
            "$TrainScript = Join-Path $ProjectRoot 'train_unsloth.py'",
            "$env:BASE_MODEL = $env:BASE_MODEL ?? 'unsloth/mistral-7b-instruct-v0.3-bnb-4bit'",
            "$env:OUTPUT_DIR = $env:OUTPUT_DIR ?? './outputs/unsloth-lora'",
            "",
            "& $PythonExe $TrainScript `",
            "  --config (Join-Path $ScriptDir 'unsloth_config.json') `",
            "  --model-name $env:BASE_MODEL `",
            f"  --train-file \"{bundle.train_path.as_posix()}\" `",
            f"  --validation-file \"{bundle.validation_path.as_posix()}\" `",
            f"  --max-seq-length {recipe.max_sequence_length} `",
            f"  --learning-rate {recipe.learning_rate} `",
            f"  --num-epochs {recipe.num_epochs} `",
            f"  --micro-batch-size {recipe.micro_batch_size} `",
            f"  --gradient-accumulation-steps {recipe.gradient_accumulation_steps} `",
            f"  --lora-r {recipe.lora_rank} `",
            f"  --lora-alpha {recipe.lora_alpha} `",
            f"  --lora-dropout {recipe.lora_dropout} `",
            "  --load-in-4bit `",
            "  --output-dir $env:OUTPUT_DIR",
        ]
    ) + "\n"


def _render_llamafactory_launch_script(bundle: TrainingFineTuneBundle) -> str:
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$env:OUTPUT_DIR = $env:OUTPUT_DIR ?? './outputs/llamafactory-lora'",
            "",
            "# Fill in your local llama-factory entrypoint if it differs from this scaffold.",
            "@'",
            "llamafactory-cli train `",
            f"  --output_dir $env:OUTPUT_DIR `",
            f"  --config \"{(bundle.bundle_dir / 'llamafactory_config.json').as_posix()}\"",
            "'@",
        ]
    ) + "\n"

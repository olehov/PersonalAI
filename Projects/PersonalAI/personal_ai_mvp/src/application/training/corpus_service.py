"""Builds synthetic supervised training examples from the vault."""

from __future__ import annotations

import json
import re
from pathlib import Path

from application.knowledge.knowledge_service import KnowledgeService
from domain.models import (
    NoteDocument,
    TrainingCorpus,
    TrainingCorpusManifest,
    TrainingCorpusSplit,
    TrainingExample,
)
from infrastructure.config.settings import get_settings


class TrainingCorpusService:
    """Creates lightweight training examples from canonical vault notes."""

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        curated_examples_dir: Path | None = None,
        ukrainian_examples_dir: Path | None = None,
    ) -> None:
        settings = get_settings()
        self._knowledge_service = knowledge_service
        self._curated_examples_dir = curated_examples_dir or settings.curated_examples_dir
        self._ukrainian_examples_dir = ukrainian_examples_dir or settings.ukrainian_examples_dir

    def build_corpus(
        self,
        *,
        limit: int = 50,
        source: str = "all",
    ) -> TrainingCorpus:
        """Builds a supervised corpus from notes that look stable and reusable."""
        examples: list[TrainingExample] = []
        seen_ids: set[str] = set()

        if source in {"all", "curated"}:
            for example in self._load_examples_from_dir(
                self._curated_examples_dir,
                default_source="curated",
            ):
                if len(examples) >= limit:
                    break
                if example.example_id in seen_ids:
                    continue
                examples.append(example)
                seen_ids.add(example.example_id)

        if source in {"all", "ukrainian"}:
            for example in self._load_examples_from_dir(
                self._ukrainian_examples_dir,
                default_source="ukrainian",
            ):
                if len(examples) >= limit:
                    break
                if example.example_id in seen_ids:
                    continue
                examples.append(example)
                seen_ids.add(example.example_id)

        if source in {"all", "synthetic"}:
            for note in self._knowledge_service.list_notes():
                if len(examples) >= limit:
                    break
                if not _is_training_candidate(note):
                    continue

                noisy_markdown = _degrade_note(note)
                example_id = f"rewrite::{note.path.as_posix()}"
                if example_id not in seen_ids:
                    examples.append(
                        TrainingExample(
                            example_id=example_id,
                            source="synthetic",
                            quality_tier="silver",
                            task="rewrite_note_to_house_style",
                            source_note_path=note.path,
                            title=note.title,
                            instruction=(
                                "Rewrite this note into the vault house style. Preserve grounded facts, "
                                "restore compact sections, use Obsidian links, and remove diagnostic/meta commentary."
                            ),
                            input_markdown=noisy_markdown,
                            target_markdown=note.content.strip() + "\n",
                            tags=_tags_for_note(note, synthetic_variant="noisy_rewrite"),
                        )
                    )
                    seen_ids.add(example_id)

                if len(examples) >= limit:
                    break

                outline_markdown = _outline_note(note)
                outline_id = f"expand::{note.path.as_posix()}"
                if outline_id not in seen_ids and outline_markdown != note.content.strip() + "\n":
                    examples.append(
                        TrainingExample(
                            example_id=outline_id,
                            source="synthetic",
                            quality_tier="silver",
                            task="expand_outline_to_note",
                            source_note_path=note.path,
                            title=note.title,
                            instruction=(
                                "Expand this outline into a complete note that matches the vault house style. "
                                "Keep headings compact and preserve the note's original structure."
                            ),
                            input_markdown=outline_markdown,
                            target_markdown=note.content.strip() + "\n",
                            tags=_tags_for_note(note, synthetic_variant="outline_expansion"),
                        )
                    )
                    seen_ids.add(outline_id)

        return TrainingCorpus(examples=tuple(examples))

    def build_manifest(
        self,
        *,
        limit: int = 50,
        source: str = "all",
    ) -> TrainingCorpusManifest:
        """Builds a compact manifest for the selected corpus slice."""
        corpus = self.build_corpus(limit=limit, source=source)
        by_source: dict[str, int] = {}
        by_quality_tier: dict[str, int] = {}
        by_task: dict[str, int] = {}

        for example in corpus.examples:
            by_source[example.source] = by_source.get(example.source, 0) + 1
            by_quality_tier[example.quality_tier] = by_quality_tier.get(example.quality_tier, 0) + 1
            by_task[example.task] = by_task.get(example.task, 0) + 1

        return TrainingCorpusManifest(
            total_examples=len(corpus.examples),
            by_source=by_source,
            by_quality_tier=by_quality_tier,
            by_task=by_task,
        )

    def build_split(
        self,
        *,
        limit: int = 50,
        source: str = "all",
        validation_ratio: float = 0.2,
    ) -> TrainingCorpusSplit:
        """Builds a deterministic split with curated gold favored for validation."""
        corpus = self.build_corpus(limit=limit, source=source)
        if not corpus.examples:
            return TrainingCorpusSplit(policy=_split_policy_description(validation_ratio))

        gold_examples = sorted(
            [example for example in corpus.examples if example.quality_tier == "gold"],
            key=lambda example: example.example_id,
        )
        silver_examples = sorted(
            [example for example in corpus.examples if example.quality_tier != "gold"],
            key=lambda example: example.example_id,
        )

        validation_target = max(1, round(len(corpus.examples) * validation_ratio))
        gold_validation_target = min(len(gold_examples), max(1, round(validation_target * 0.6)))
        silver_validation_target = max(validation_target - gold_validation_target, 0)

        validation_examples = [
            *gold_examples[:gold_validation_target],
            *silver_examples[:silver_validation_target],
        ]
        if len(validation_examples) < validation_target:
            selected_ids = {example.example_id for example in validation_examples}
            gold_fill = [
                example for example in gold_examples
                if example.example_id not in selected_ids
            ]
            silver_fill = [
                example for example in silver_examples
                if example.example_id not in selected_ids
            ]
            for example in [*gold_fill, *silver_fill]:
                if len(validation_examples) >= validation_target:
                    break
                validation_examples.append(example)
                selected_ids.add(example.example_id)
        validation_ids = {example.example_id for example in validation_examples}
        train_examples = [
            example for example in corpus.examples
            if example.example_id not in validation_ids
        ]

        return TrainingCorpusSplit(
            train_examples=tuple(train_examples),
            validation_examples=tuple(validation_examples),
            policy=_split_policy_description(validation_ratio),
        )

    def _load_examples_from_dir(
        self,
        examples_dir: Path,
        *,
        default_source: str,
    ) -> tuple[TrainingExample, ...]:
        if not examples_dir.exists():
            return ()

        examples: list[TrainingExample] = []
        for path in sorted(examples_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            examples.append(
                TrainingExample(
                    example_id=payload["example_id"],
                    source=payload.get("source", default_source),
                    quality_tier=payload.get("quality_tier", "gold"),
                    task=payload["task"],
                    source_note_path=Path(payload["source_note_path"]),
                    title=payload["title"],
                    instruction=payload["instruction"],
                    input_markdown=payload["input_markdown"],
                    target_markdown=payload["target_markdown"],
                    tags=tuple(payload.get("tags", ())),
                )
            )
        return tuple(examples)


def _is_training_candidate(note: NoteDocument) -> bool:
    content = note.content.strip()
    if not content:
        return False
    if len(_words(content)) < 12:
        return False
    path = note.path.as_posix().casefold()
    if ".history/" in path or "/archive/" in path:
        return False
    return True


def _degrade_note(note: NoteDocument) -> str:
    text = note.content.strip()
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"[\2](/\1.md)", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"[\1](/\1.md)", text)
    text = re.sub(r"(?m)^- ([A-Za-z][^\n:]{2,30})$", lambda match: f"- **{match.group(1).title()}**", text)
    text = text.replace("Responsibilities:", "Key responsibilities:")
    text = re.sub(r"(?m)^### (\d+)\s*$", r"### \1. Placeholder", text)
    if "## Future" in text and "## Missing Knowledge" not in text:
        text += "\n\n## Missing Knowledge\nFurther context may be needed.\n"
    return text.strip() + "\n"


def _outline_note(note: NoteDocument) -> str:
    lines = note.content.strip().splitlines()
    outline: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            outline.append(stripped)
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            outline.append(stripped)
            continue
        if stripped.startswith("- "):
            outline.append(stripped)
            continue
        if len(outline) == 0 or not outline[-1].startswith("#"):
            continue
        outline.append(f"- note: {stripped}")
    return "\n".join(outline).strip() + "\n"


def _tags_for_note(note: NoteDocument, *, synthetic_variant: str) -> tuple[str, ...]:
    tags = [synthetic_variant]
    top_level = note.path.parts[0] if note.path.parts else "root"
    tags.append(top_level.casefold())

    content = note.content
    if "Responsibilities:" in content:
        tags.append("responsibilities")
    if re.search(r"(?m)^### \d+\s*$", content):
        tags.append("numbered_sections")
    if "[[" in content:
        tags.append("obsidian_links")
    return tuple(tags)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text)


def _split_policy_description(validation_ratio: float) -> str:
    return (
        f"Deterministic split with validation_ratio={validation_ratio:.2f}. "
        "Gold curated examples are favored for validation before silver synthetic examples."
    )

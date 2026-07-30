"""JSONL dataset rendering helpers for training CLI workflows."""

from __future__ import annotations

import json


def render_training_corpus_jsonl(
    examples: list[dict[str, object]],
    *,
    mode: str,
) -> str:
    """Render training examples as JSONL chat or completion records."""
    lines: list[str] = []
    for example in examples:
        if mode == "chat":
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
                            f"Task: {example['task']}\n"
                            f"Title: {example['title']}\n"
                            f"Instruction: {example['instruction']}\n\n"
                            "Input note:\n```md\n"
                            f"{example['input_markdown']}```"
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": example["target_markdown"],
                    },
                ],
                "metadata": {
                    "example_id": example["example_id"],
                    "source_note_path": example["source_note_path"],
                    "tags": example["tags"],
                },
            }
        else:
            record = {
                "prompt": (
                    "Rewrite this Obsidian note into the vault house style.\n"
                    f"Task: {example['task']}\n"
                    f"Title: {example['title']}\n"
                    f"Instruction: {example['instruction']}\n\n"
                    "Input note:\n```md\n"
                    f"{example['input_markdown']}```\n\n"
                    "Rewritten note:\n"
                ),
                "completion": example["target_markdown"],
                "metadata": {
                    "example_id": example["example_id"],
                    "source_note_path": example["source_note_path"],
                    "tags": example["tags"],
                },
            }
        lines.append(json.dumps(record, ensure_ascii=True))
    return "\n".join(lines)


def select_split_examples(payload: dict[str, object], subset: str) -> list[dict[str, object]]:
    """Select train, validation, or combined examples from a split payload."""
    if subset == "train":
        return list(payload["train_examples"])
    if subset == "validation":
        return list(payload["validation_examples"])
    return [*list(payload["train_examples"]), *list(payload["validation_examples"])]

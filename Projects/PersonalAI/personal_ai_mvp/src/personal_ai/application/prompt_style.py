"""Vault-specific prompt style guidance built from existing notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from personal_ai.domain.models import NoteDocument


@dataclass(frozen=True, slots=True)
class PromptStylePack:
    """Compact style guidance with small in-vault examples."""

    guidance: tuple[str, ...] = field(default_factory=tuple)
    examples: tuple[str, ...] = field(default_factory=tuple)


def build_prompt_style_pack(
    *,
    notes: tuple[NoteDocument, ...],
    authoritative_text: str = "",
) -> PromptStylePack:
    """Builds a small house-style pack from existing vault material."""
    guidance = [
        "Use Obsidian markdown only.",
        "Prefer compact sections and bullets over explanatory prose.",
        "Use internal links as [[Note Title]] and avoid markdown web links.",
        "Preserve existing section structure when the current note already has a good template.",
        "Do not add meta sections like Open Questions or Missing Knowledge unless the note already uses them.",
    ]

    examples: list[str] = []
    seen_examples: set[str] = set()

    authority_examples = _extract_style_examples(authoritative_text)
    for example in authority_examples:
        if example not in seen_examples:
            examples.append(example)
            seen_examples.add(example)
        if len(examples) >= 3:
            break

    for note in notes:
        for example in _extract_style_examples(note.content):
            if example in seen_examples:
                continue
            examples.append(example)
            seen_examples.add(example)
            if len(examples) >= 3:
                break
        if len(examples) >= 3:
            break

    if authoritative_text and _has_numeric_subsections(authoritative_text):
        guidance.append("Keep numbered subsection templates compact, for example `### 1` followed by a short stub.")
    if authoritative_text and "Responsibilities:" in authoritative_text:
        guidance.append("When a section uses `Responsibilities:`, keep that exact label and preserve short bullet wording.")

    return PromptStylePack(
        guidance=tuple(guidance),
        examples=tuple(examples),
    )


def render_prompt_style_pack(style_pack: PromptStylePack) -> str:
    """Renders a prompt style pack as compact prompt text."""
    if not style_pack.guidance and not style_pack.examples:
        return ""

    lines = ["Vault Style Guide:"]
    for item in style_pack.guidance:
        lines.append(f"- {item}")

    if style_pack.examples:
        lines.extend(["", "Canonical Examples:"])
        for example in style_pack.examples:
            lines.append("```md")
            lines.append(example)
            lines.append("```")

    return "\n".join(lines)


def _extract_style_examples(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()

    examples: list[str] = []
    responsibilities = _extract_responsibilities_block(text)
    if responsibilities:
        examples.append(responsibilities)

    numeric = _extract_numeric_subsection(text)
    if numeric:
        examples.append(numeric)

    stub = _extract_short_stub_section(text)
    if stub:
        examples.append(stub)

    return tuple(examples)


def _extract_responsibilities_block(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "Responsibilities:":
            continue

        block = [line.strip()]
        cursor = index + 1
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if not stripped:
                cursor += 1
                continue
            if stripped.startswith("- "):
                block.append(stripped)
                cursor += 1
                continue
            break

        if len(block) >= 2:
            return "\n".join(block)
    return None


def _extract_numeric_subsection(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r"^\s*#{2,}\s+\d+\s*$", line):
            continue

        block = [line.strip()]
        cursor = index + 1
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if not stripped:
                cursor += 1
                continue
            if stripped.startswith("#"):
                break
            block.append(stripped)
            break

        if len(block) >= 2:
            return "\n".join(block)
    return None


def _extract_short_stub_section(text: str) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.strip().startswith("### "):
            continue

        heading = line.strip()
        cursor = index + 1
        body: list[str] = []
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if not stripped:
                cursor += 1
                continue
            if stripped.startswith("#"):
                break
            body.append(stripped)
            cursor += 1
            break

        if len(body) != 1:
            continue
        if body[0].endswith(":") or body[0].startswith("- "):
            continue
        if len(re.findall(r"[A-Za-z0-9_]{2,}", body[0])) > 4:
            continue
        return f"{heading}\n{body[0]}"
    return None


def _has_numeric_subsections(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*#{2,}\s+\d+\s*$", text))

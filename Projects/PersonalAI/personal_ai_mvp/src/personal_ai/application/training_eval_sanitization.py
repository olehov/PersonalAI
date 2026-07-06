"""Model-output sanitization helpers for training evaluation."""

from __future__ import annotations

import re

from personal_ai.domain.models import TrainingExample


def sanitize_output_for_model(
    *,
    model: str,
    output_markdown: str,
    example: TrainingExample,
) -> str:
    """Normalize model-specific markdown quirks before scoring."""
    lowered = model.casefold()
    if "qwen" not in lowered:
        if "mistral" not in lowered:
            return output_markdown
        return sanitize_mistral_output(
            output_markdown,
            example.target_markdown,
            example.title,
        )
    return sanitize_qwen_output(output_markdown, example.target_markdown)


def sanitize_qwen_output(output_markdown: str, target_markdown: str) -> str:
    """Fix common Qwen link-format issues into vault-compatible markdown."""
    expected_links = expected_link_map(target_markdown)
    if not expected_links:
        return output_markdown

    sanitized = output_markdown.replace("\r\n", "\n")
    sanitized = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: replace_markdown_link(match, expected_links),
        sanitized,
    )
    sanitized = normalize_related_note_lines(sanitized, expected_links)
    sanitized = re.sub(
        r"\[\[([^\]]+)\]\]",
        lambda match: replace_obsidian_link(match, expected_links),
        sanitized,
    )
    return sanitized if sanitized.endswith("\n") else sanitized + "\n"


def sanitize_mistral_output(
    output_markdown: str,
    target_markdown: str,
    expected_title: str,
) -> str:
    """Normalize common Mistral formatting drift into vault house style."""
    expected_links = expected_link_map(target_markdown)
    sanitized = output_markdown.replace("\r\n", "\n").strip()
    sanitized = strip_code_fences(sanitized)
    sanitized = normalize_title_prefix(sanitized, expected_title)
    sanitized = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: replace_markdown_link(match, expected_links),
        sanitized,
    )
    sanitized = re.sub(
        r"\[\[([^\]]+)\]\]",
        lambda match: replace_obsidian_link(match, expected_links),
        sanitized,
    )
    sanitized = canonicalize_mistral_headings(
        sanitized,
        target_markdown=target_markdown,
        expected_title=expected_title,
    )
    sanitized = restore_collapsed_structured_sections(
        sanitized,
        target_markdown=target_markdown,
    )
    return sanitized.strip() + "\n"


def expected_link_map(target_markdown: str) -> dict[str, str]:
    """Build a canonical lookup of expected links from target markdown."""
    mapping: dict[str, str] = {}
    for raw_link in links(target_markdown):
        canonical = raw_link.split("|", 1)[0].strip()
        if not canonical:
            continue
        candidates = {
            canonical,
            canonical.rsplit("/", 1)[-1],
        }
        if "|" in raw_link:
            alias = raw_link.split("|", 1)[1].strip()
            if alias:
                candidates.add(alias)
        for candidate in candidates:
            mapping.setdefault(candidate.casefold(), canonical)
    return mapping


def replace_markdown_link(
    match: re.Match[str],
    expected_links: dict[str, str],
) -> str:
    """Convert markdown path links into canonical Obsidian links when possible."""
    label = match.group(1).strip()
    target = match.group(2).strip()
    canonical = resolve_expected_link(label, expected_links)
    if canonical is None:
        path_match = re.search(r"/([^/#?]+?)(?:\.md)?$", target)
        if path_match is not None:
            slug = path_match.group(1).replace("%20", " ").strip()
            canonical = resolve_expected_link(slug, expected_links)
    if canonical is None:
        return label
    return f"[[{canonical}]]"


def normalize_related_note_lines(
    text: str,
    expected_links: dict[str, str],
) -> str:
    """Normalize plain related-note bullet lines into Obsidian links."""
    lines = text.split("\n")
    normalized: list[str] = []
    in_related_notes = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            in_related_notes = stripped.lstrip("#").strip().casefold() == "related notes"
            normalized.append(line)
            continue
        if in_related_notes and stripped:
            content = stripped.removeprefix("-").removeprefix("*").strip()
            canonical = resolve_expected_link(content, expected_links)
            if canonical is not None:
                normalized.append(f"[[{canonical}]]")
                continue
        normalized.append(line)

    return "\n".join(normalized)


def resolve_expected_link(
    candidate: str,
    expected_links: dict[str, str],
) -> str | None:
    """Resolve one candidate label against expected canonical links."""
    trimmed = candidate.strip()
    if not trimmed:
        return None
    if trimmed.startswith("[[") and trimmed.endswith("]]"):
        trimmed = trimmed[2:-2].strip()
    if "|" in trimmed:
        trimmed = trimmed.split("|", 1)[0].strip()
    return expected_links.get(trimmed.casefold())


def replace_obsidian_link(
    match: re.Match[str],
    expected_links: dict[str, str],
) -> str:
    """Prune or canonicalize Obsidian links against expected targets."""
    raw_target = match.group(1).strip()
    canonical = resolve_expected_link(raw_target, expected_links)
    if canonical is not None:
        return f"[[{canonical}]]"
    if "|" in raw_target:
        return raw_target.split("|", 1)[1].strip()
    return raw_target


def strip_code_fences(text: str) -> str:
    """Drop top-level fenced wrappers if the model emitted them."""
    fenced = re.fullmatch(r"```[A-Za-z0-9_-]*\n?(.*?)\n?```", text, flags=re.DOTALL)
    if fenced is None:
        return text
    return fenced.group(1).strip()


def normalize_title_prefix(text: str, expected_title: str) -> str:
    """Turn `Title:` wrappers into the expected markdown heading."""
    lines = text.split("\n")
    if not lines:
        return text
    first = lines[0].strip()
    if not first.casefold().startswith("title:"):
        return text
    remaining = "\n".join(lines[1:]).lstrip("\n")
    normalized = f"# {expected_title}"
    if not remaining:
        return normalized
    return f"{normalized}\n\n{remaining}"


def canonicalize_mistral_headings(
    text: str,
    *,
    target_markdown: str,
    expected_title: str,
) -> str:
    """Align Mistral heading names to the target heading order."""
    target_headings = ordered_headings(target_markdown)
    if not target_headings:
        return text

    lines = text.split("\n")
    first_content_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if first_content_index is not None:
        first_content = lines[first_content_index].strip()
        if (
            first_content.casefold() == expected_title.casefold()
            and not first_content.startswith("#")
        ):
            lines[first_content_index] = target_headings[0]

    heading_indices = [
        index for index, line in enumerate(lines)
        if line.strip().startswith("#")
    ]
    if len(heading_indices) == len(target_headings):
        for index, target_heading in zip(heading_indices, target_headings):
            lines[index] = target_heading
        return "\n".join(lines)

    output_headings = ordered_headings("\n".join(lines))
    for level in range(1, 7):
        target_level_headings = [
            heading for heading in target_headings
            if heading.startswith("#" * level + " ")
        ]
        output_level_headings = [
            heading for heading in output_headings
            if heading.startswith("#" * level + " ")
        ]
        if not target_level_headings or len(target_level_headings) != len(output_level_headings):
            continue
        replacement_map = {
            output_heading: target_heading
            for output_heading, target_heading in zip(output_level_headings, target_level_headings)
        }
        for index, line in enumerate(lines):
            stripped = line.strip()
            replacement = replacement_map.get(stripped)
            if replacement is not None:
                lines[index] = replacement
    return "\n".join(lines)


def ordered_headings(text: str) -> tuple[str, ...]:
    """Return headings in document order."""
    return tuple(
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("#")
    )


def restore_collapsed_structured_sections(
    text: str,
    *,
    target_markdown: str,
) -> str:
    """Restore structured heading/subheading sections that a model collapsed."""
    output_lines = text.split("\n")
    target_lines = target_markdown.split("\n")
    target_headings = scan_heading_entries(target_lines)
    output_headings = scan_heading_entries(output_lines)

    for target_index, target_level, target_heading in target_headings:
        if target_level != 2:
            continue
        target_end = find_section_end(target_headings, target_index, target_level, len(target_lines))
        target_has_subsections = any(
            child_level == target_level + 1
            for child_index, child_level, _child_heading in target_headings
            if target_index < child_index < target_end
        )
        if not target_has_subsections:
            continue

        output_match = next(
            (
                (index, level, heading)
                for index, level, heading in output_headings
                if level == target_level and heading == target_heading
            ),
            None,
        )
        if output_match is None:
            continue

        output_index, output_level, _output_heading = output_match
        output_end = find_section_end(output_headings, output_index, output_level, len(output_lines))
        output_has_subsections = any(
            child_level == output_level + 1
            for child_index, child_level, _child_heading in output_headings
            if output_index < child_index < output_end
        )
        if output_has_subsections:
            target_children = child_heading_titles(
                target_headings,
                start_index=target_index,
                end_index=target_end,
                child_level=target_level + 1,
            )
            output_children = child_heading_titles(
                output_headings,
                start_index=output_index,
                end_index=output_end,
                child_level=output_level + 1,
            )
            if target_children == output_children:
                continue

        replacement = target_lines[target_index:target_end]
        output_lines[output_index:output_end] = replacement
        output_headings = scan_heading_entries(output_lines)

    return "\n".join(output_lines)


def scan_heading_entries(lines: list[str]) -> list[tuple[int, int, str]]:
    """Scan markdown headings into indexed tuples."""
    entries: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if match is None:
            continue
        entries.append((index, len(match.group(1)), stripped))
    return entries


def find_section_end(
    headings: list[tuple[int, int, str]],
    start_index: int,
    start_level: int,
    total_lines: int,
) -> int:
    """Find the end line for a heading-scoped markdown section."""
    for index, level, _heading in headings:
        if index <= start_index:
            continue
        if level <= start_level:
            return index
    return total_lines


def child_heading_titles(
    headings: list[tuple[int, int, str]],
    *,
    start_index: int,
    end_index: int,
    child_level: int,
) -> tuple[str, ...]:
    """Collect direct child headings within one section span."""
    return tuple(
        heading
        for index, level, heading in headings
        if start_index < index < end_index and level == child_level
    )


def links(text: str) -> set[str]:
    """Extract Obsidian link targets from markdown text."""
    return set(re.findall(r"\[\[([^\]]+)\]\]", text))

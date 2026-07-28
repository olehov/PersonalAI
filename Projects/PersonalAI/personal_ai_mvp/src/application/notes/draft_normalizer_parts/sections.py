"""Section-level normalization helpers for generated notes."""

from __future__ import annotations

import re

from application.notes.draft_normalizer_parts.authority import (
    extract_headings,
    normalize_heading_text,
)
from application.notes.draft_normalizer_parts.grounding import (
    content_tokens,
    is_grounded_clause,
)


def prune_structured_section_intros(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    authority_sections = extract_canonical_section_bodies(authoritative_text)
    authority_container_headings = extract_container_headings(authoritative_text)
    if not authority_sections:
        authority_sections = {}
    if not authority_sections and not authority_container_headings:
        return text

    blocks = split_heading_blocks(text.splitlines())
    cleaned_blocks: list[list[str]] = []
    for heading, block_lines in blocks:
        if heading is None:
            cleaned_blocks.append(block_lines)
            continue

        normalized_heading = normalize_heading_text(heading)
        authority_body = authority_sections.get(normalized_heading)
        if authority_body and has_structured_authority_body(authority_body):
            cleaned_blocks.append(remove_intro_lines_from_structured_block(block_lines, authority_body))
            continue

        if authority_body and has_intro_plus_bullets_authority_body(authority_body):
            cleaned_blocks.append(normalize_intro_plus_bullets_block(block_lines, authority_body))
            continue

        if authority_body and has_subheading_only_authority_body(authority_body):
            cleaned_blocks.append(remove_container_intro_block(block_lines))
            continue

        if normalized_heading in authority_container_headings:
            cleaned_blocks.append(remove_container_intro_block(block_lines))
            continue

        cleaned_blocks.append(block_lines)

    return "\n".join(line for block in cleaned_blocks for line in block)


def canonicalize_known_sections(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    authority_sections = extract_canonical_section_bodies(authoritative_text)
    if not authority_sections:
        return text

    lines = text.splitlines()
    blocks = split_heading_blocks(lines)
    canonicalized: list[str] = []
    for heading, block_lines in blocks:
        if heading is None:
            canonicalized.extend(block_lines)
            continue

        normalized_heading = normalize_heading_text(heading)
        authority_body = authority_sections.get(normalized_heading)
        if authority_body is None:
            canonicalized.extend(block_lines)
            continue

        if should_canonicalize_section(authority_body, block_lines):
            canonicalized.extend(render_canonical_section(block_lines[0], authority_body))
            continue

        canonicalized.extend(block_lines)

    return "\n".join(canonicalized)


def extract_section_bodies(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_heading is not None:
                sections[current_heading] = current_body[:]
            current_heading = normalize_heading_text(stripped.lstrip("#").strip())
            current_body = []
            continue
        if current_heading is not None:
            current_body.append(line.rstrip())
    if current_heading is not None:
        sections[current_heading] = current_body[:]
    return sections


def extract_canonical_section_bodies(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    current_level = 0
    current_body: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_heading is not None and current_level >= 2:
                sections[current_heading] = trim_canonical_section_body(current_body)
            current_level = len(stripped) - len(stripped.lstrip("#"))
            current_heading = normalize_heading_text(stripped.lstrip("#").strip())
            current_body = []
            continue
        if stripped == "---" and current_heading is not None and current_level >= 2:
            sections[current_heading] = trim_canonical_section_body(current_body)
            current_heading = None
            current_level = 0
            current_body = []
            continue
        if current_heading is not None:
            current_body.append(line.rstrip())
    if current_heading is not None and current_level >= 2:
        sections[current_heading] = trim_canonical_section_body(current_body)
    return sections


def extract_container_headings(text: str) -> set[str]:
    lines = text.splitlines()
    containers: set[str] = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        if level < 2:
            continue

        heading = normalize_heading_text(stripped.lstrip("#").strip())
        next_nonempty = None
        for candidate in lines[index + 1:]:
            candidate_stripped = candidate.strip()
            if candidate_stripped:
                next_nonempty = candidate_stripped
                break

        if next_nonempty is None:
            continue
        if not next_nonempty.startswith("#"):
            continue

        next_level = len(next_nonempty) - len(next_nonempty.lstrip("#"))
        if next_level > level:
            containers.add(heading)
    return containers


def split_heading_blocks(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    blocks: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_lines:
                blocks.append((current_heading, current_lines[:]))
            current_heading = stripped.lstrip("#").strip()
            current_lines = [line]
            continue
        if not current_lines:
            current_lines = [line]
            continue
        current_lines.append(line)
    if current_lines:
        blocks.append((current_heading, current_lines[:]))
    return blocks


def should_canonicalize_section(authority_body: list[str], block_lines: list[str]) -> bool:
    authority_content = [line.strip() for line in authority_body if line.strip()]
    if not authority_content:
        return False

    if should_restore_structured_section(authority_content, block_lines):
        return True
    if should_restore_intro_plus_bullets_section(authority_content, block_lines):
        return True
    if should_restore_stub_section(authority_content, block_lines):
        return True

    if len(authority_content) > 3:
        return False

    authority_tokens = content_tokens(" ".join(authority_content))
    if len(authority_tokens) > 8:
        return False

    generated_content = meaningful_block_content(block_lines[1:])
    if not generated_content:
        return False

    generated_tokens = content_tokens(" ".join(generated_content))
    if len(generated_tokens) <= len(authority_tokens) + 2:
        return False

    return True


def should_restore_structured_section(authority_content: list[str], block_lines: list[str]) -> bool:
    if len(authority_content) < 2:
        return False

    label_line = authority_content[0]
    if not label_line.endswith(":") or label_line.startswith("-"):
        return False

    bullet_lines = authority_content[1:]
    if not bullet_lines or len(bullet_lines) > 5:
        return False
    if any(not line.startswith("- ") for line in bullet_lines):
        return False

    generated_content = [line.strip() for line in block_lines[1:] if line.strip()]
    if not generated_content:
        return False

    if label_line in generated_content:
        return False

    return any(not line.startswith("- ") for line in generated_content)


def should_restore_stub_section(authority_content: list[str], block_lines: list[str]) -> bool:
    if len(authority_content) != 1:
        return False

    authority_line = authority_content[0]
    if authority_line.endswith(":") or authority_line.startswith("- "):
        return False

    authority_tokens = content_tokens(authority_line)
    if not authority_tokens or len(authority_tokens) > 4:
        return False

    generated_content = meaningful_block_content(block_lines[1:])
    if len(generated_content) != 1:
        return False

    generated_line = generated_content[0]
    if generated_line == authority_line:
        return False

    generated_tokens = content_tokens(generated_line)
    if not authority_tokens:
        return False

    overlap = len(authority_tokens & generated_tokens)
    if overlap < max(1, len(authority_tokens) - 1):
        return False

    authority_normalized = authority_line.casefold().strip().rstrip(".")
    generated_normalized = generated_line.casefold().strip().rstrip(".")
    if authority_normalized != generated_normalized and overlap == len(authority_tokens):
        return True

    heading_tokens = content_tokens(block_lines[0].lstrip("#").strip())
    repeats_heading = bool(heading_tokens & generated_tokens)
    is_verbose = len(generated_tokens) > len(authority_tokens)
    return repeats_heading or is_verbose


def should_restore_intro_plus_bullets_section(authority_content: list[str], block_lines: list[str]) -> bool:
    if not has_intro_plus_bullets_authority_body(authority_content):
        return False

    generated_content = meaningful_block_content(block_lines[1:])
    if not generated_content:
        return False

    intro_line = authority_content[0].strip()
    intro_tokens = content_tokens(intro_line)
    bullet_count = sum(1 for line in generated_content if line.startswith("- "))
    prose_count = sum(1 for line in generated_content if not line.startswith("- "))

    if prose_count == 0:
        return False

    if intro_line not in generated_content:
        return True

    if bullet_count >= max(1, len(authority_content) - 2):
        return True

    if intro_tokens and any(
        len(content_tokens(line) - intro_tokens) >= 4
        for line in generated_content
        if not line.startswith("- ")
    ):
        return True

    return False


def render_canonical_section(heading_line: str, authority_body: list[str]) -> list[str]:
    rendered = [heading_line]
    for line in authority_body:
        rendered.append(line)
    return rendered


def restore_missing_authoritative_heading_blocks(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    if not authoritative_text.strip():
        return text

    content_lines = text.splitlines()
    content_headings = {
        normalize_heading_text(heading)
        for heading in extract_headings(text)
    }
    authority_blocks = split_heading_blocks(authoritative_text.splitlines())

    for index, (heading, block_lines) in enumerate(authority_blocks):
        if heading is None or not block_lines:
            continue

        normalized_heading = normalize_heading_text(heading)
        if normalized_heading in content_headings:
            continue

        heading_line = next(
            (line for line in block_lines if line.strip().startswith("#")),
            None,
        )
        if heading_line is None:
            continue

        heading_level = heading_level_of(heading_line)
        parent_heading = find_authority_parent_heading(authority_blocks, index, heading_level)
        insert_at = len(content_lines)
        if parent_heading is not None:
            parent_index = find_heading_line_index(content_lines, parent_heading)
            if parent_index is not None:
                parent_level = heading_level_of(content_lines[parent_index])
                insert_at = find_section_end_index(content_lines, parent_index, parent_level)

        block_to_insert = prepare_insertable_block(block_lines)
        if not block_to_insert:
            continue

        if insert_at > 0 and content_lines[insert_at - 1].strip():
            block_to_insert = ["", *block_to_insert]
        if insert_at < len(content_lines) and content_lines[insert_at].strip():
            block_to_insert = [*block_to_insert, ""]

        content_lines[insert_at:insert_at] = block_to_insert
        content_headings.add(normalized_heading)

    return "\n".join(content_lines)


def normalize_section_spacing(text: str) -> str:
    lines = text.splitlines()
    normalized: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            if normalized and normalized[-1] != "":
                normalized.append("")
            normalized.append(stripped)

            next_nonempty = None
            for candidate in lines[index + 1:]:
                candidate_stripped = candidate.strip()
                if candidate_stripped:
                    next_nonempty = candidate_stripped
                    break
            if next_nonempty is not None:
                normalized.append("")
            continue

        if stripped == "":
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue

        normalized.append(line.rstrip())

    while normalized and normalized[-1] == "":
        normalized.pop()
    return "\n".join(normalized)


def strip_unsupported_open_questions(
    text: str,
    *,
    grounded_tokens: set[str],
    authoritative_text: str,
) -> str:
    authority_headings = {
        normalize_heading_text(heading)
        for heading in extract_headings(authoritative_text)
    }
    if "open questions" in authority_headings:
        return text

    blocks = split_heading_blocks(text.splitlines())
    if not any(
        heading is not None and normalize_heading_text(heading) == "open questions"
        for heading, _ in blocks
    ):
        return text

    if authoritative_text.strip():
        filtered_blocks = [
            block_lines
            for heading, block_lines in blocks
            if heading is None or normalize_heading_text(heading) != "open questions"
        ]
        flattened: list[str] = []
        for index, block in enumerate(filtered_blocks):
            if index > 0 and flattened and flattened[-1] != "":
                flattened.append("")
            flattened.extend(block)
        return "\n".join(flattened)

    cleaned_blocks: list[list[str]] = []
    for heading, block_lines in blocks:
        if heading is None:
            cleaned_blocks.append(block_lines)
            continue
        if normalize_heading_text(heading) != "open questions":
            cleaned_blocks.append(block_lines)
            continue

        kept_lines = [block_lines[0]]
        for line in block_lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                clause = stripped[2:].strip()
                if is_grounded_clause(clause, grounded_tokens):
                    kept_lines.append(line)
                continue
            if is_grounded_clause(stripped, grounded_tokens):
                kept_lines.append(line)

        if len(kept_lines) > 1:
            cleaned_blocks.append(kept_lines)

    flattened: list[str] = []
    for index, block in enumerate(cleaned_blocks):
        if index > 0 and flattened and flattened[-1] != "":
            flattened.append("")
        flattened.extend(block)
    return "\n".join(flattened)


def strip_unsupported_diagnostic_sections(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    authority_headings = {
        normalize_heading_text(heading)
        for heading in extract_headings(authoritative_text)
    }
    blocked_headings = {
        "missing knowledge",
        "knowledge gaps",
        "missing context",
    }
    blocked_headings -= authority_headings
    if not blocked_headings:
        return text

    blocks = split_heading_blocks(text.splitlines())
    if not any(
        heading is not None and normalize_heading_text(heading) in blocked_headings
        for heading, _ in blocks
    ):
        return text

    filtered_blocks = [
        block_lines
        for heading, block_lines in blocks
        if heading is None or normalize_heading_text(heading) not in blocked_headings
    ]
    flattened: list[str] = []
    for index, block in enumerate(filtered_blocks):
        if index > 0 and flattened and flattened[-1] != "":
            flattened.append("")
        flattened.extend(block)
    return "\n".join(flattened)


def trim_canonical_section_body(lines: list[str]) -> list[str]:
    trimmed = lines[:]
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return trimmed


def meaningful_block_content(lines: list[str]) -> list[str]:
    return [
        line.strip()
        for line in lines
        if line.strip() and not re.fullmatch(r"-{3,}", line.strip())
    ]


def heading_level_of(line: str) -> int:
    stripped = line.strip()
    return len(stripped) - len(stripped.lstrip("#"))


def find_authority_parent_heading(
    authority_blocks: list[tuple[str | None, list[str]]],
    child_index: int,
    child_level: int,
) -> str | None:
    for index in range(child_index - 1, -1, -1):
        heading, block_lines = authority_blocks[index]
        if heading is None or not block_lines:
            continue
        heading_line = next(
            (line for line in block_lines if line.strip().startswith("#")),
            None,
        )
        if heading_line is None:
            continue
        if heading_level_of(heading_line) < child_level:
            return heading
    return None


def find_heading_line_index(lines: list[str], heading: str) -> int | None:
    normalized_heading = normalize_heading_text(heading)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        if normalize_heading_text(stripped.lstrip("#").strip()) == normalized_heading:
            return index
    return None


def find_section_end_index(lines: list[str], start_index: int, heading_level: int) -> int:
    for index in range(start_index + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped.startswith("#"):
            continue
        if heading_level_of(stripped) <= heading_level:
            return index
    return len(lines)


def prepare_insertable_block(block_lines: list[str]) -> list[str]:
    prepared = [line.rstrip() for line in block_lines]
    while prepared and not prepared[0].strip():
        prepared.pop(0)
    while prepared and not prepared[-1].strip():
        prepared.pop()
    return prepared


def has_structured_authority_body(authority_body: list[str]) -> bool:
    if len(authority_body) < 2:
        return False

    first_line = authority_body[0].strip()
    if not first_line.endswith(":") or first_line.startswith("-"):
        return False

    bullet_lines = [line.strip() for line in authority_body[1:] if line.strip()]
    return bool(bullet_lines) and all(line.startswith("- ") for line in bullet_lines)


def has_intro_plus_bullets_authority_body(authority_body: list[str] | list[str]) -> bool:
    if len(authority_body) < 2:
        return False

    content = [line.strip() for line in authority_body if line.strip()]
    if len(content) < 2:
        return False

    intro_line = content[0]
    if intro_line.startswith(("#", "- ")) or intro_line.endswith(":"):
        return False

    bullet_lines = content[1:]
    return bool(bullet_lines) and all(line.startswith("- ") for line in bullet_lines)


def remove_intro_lines_from_structured_block(block_lines: list[str], authority_body: list[str]) -> list[str]:
    if len(block_lines) <= 1:
        return block_lines

    label_line = authority_body[0].strip()
    body_lines = block_lines[1:]
    kept_body: list[str] = []
    found_structure = False
    for line in body_lines:
        stripped = line.strip()
        if not found_structure and stripped == label_line:
            found_structure = True
            kept_body.append(line)
            continue
        if not found_structure and stripped.startswith("- "):
            found_structure = True
            if not kept_body or kept_body[-1].strip() != label_line:
                kept_body.append(label_line)
            kept_body.append(line)
            continue
        if found_structure:
            if not stripped or stripped.startswith("- "):
                kept_body.append(line)

    if not found_structure:
        return block_lines
    return [block_lines[0], *kept_body]


def normalize_intro_plus_bullets_block(block_lines: list[str], authority_body: list[str]) -> list[str]:
    if len(block_lines) <= 1:
        return block_lines

    content = [line.strip() for line in authority_body if line.strip()]
    if len(content) < 2:
        return block_lines

    intro_line = content[0]
    body_lines = block_lines[1:]
    bullet_lines: list[str] = []
    found_bullets = False
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            found_bullets = True
            bullet_lines.append(line.rstrip())
            continue
        if found_bullets and not stripped:
            bullet_lines.append("")

    if not found_bullets:
        return block_lines

    while bullet_lines and bullet_lines[-1] == "":
        bullet_lines.pop()

    return [block_lines[0], "", intro_line, "", *bullet_lines]


def has_subheading_only_authority_body(authority_body: list[str]) -> bool:
    content = [line.strip() for line in authority_body if line.strip()]
    if not content:
        return False
    return content[0].startswith("#")


def remove_container_intro_block(block_lines: list[str]) -> list[str]:
    if len(block_lines) <= 1:
        return block_lines
    if any(line.strip() for line in block_lines[1:]):
        return [block_lines[0]]
    return block_lines


def looks_structurally_weaker_than_authority(content: str, authoritative_text: str) -> bool:
    authority_headings = extract_headings(authoritative_text)
    if authority_headings:
        content_headings = set(extract_headings(content))
        if any(heading not in content_headings for heading in authority_headings):
            return True

    authority_label_lines = {
        line.strip()
        for line in authoritative_text.splitlines()
        if line.strip().endswith(":")
    }
    if authority_label_lines:
        content_label_lines = {
            line.strip()
            for line in content.splitlines()
            if line.strip().endswith(":")
        }
        if any(label not in content_label_lines for label in authority_label_lines):
            return True

    if "Open Questions" in content and "Open Questions" not in authoritative_text:
        return True

    authority_positive = authoritative_text.count("Positive:")
    authority_negative = authoritative_text.count("Negative:")
    content_positive = content.count("Positive:")
    content_negative = content.count("Negative:")
    if content_positive > authority_positive or content_negative != authority_negative:
        return True

    authority_sections = extract_canonical_section_bodies(authoritative_text)
    content_sections = extract_canonical_section_bodies(content)
    for heading, authority_body in authority_sections.items():
        authority_content = meaningful_block_content(authority_body)
        if not authority_content:
            continue

        content_body = content_sections.get(heading)
        if content_body is None:
            return True

        content_meaningful = meaningful_block_content(content_body)
        if authority_content and not content_meaningful:
            return True

        if has_structured_authority_body(authority_body):
            authority_bullets = [
                line for line in authority_content[1:]
                if line.startswith("- ")
            ]
            content_bullets = [
                line for line in content_meaningful[1:]
                if line.startswith("- ")
            ]
            if len(content_bullets) < len(authority_bullets):
                return True

        if has_intro_plus_bullets_authority_body(authority_body):
            authority_bullets = [
                line for line in authority_content[1:]
                if line.startswith("- ")
            ]
            content_bullets = [
                line for line in content_meaningful[1:]
                if line.startswith("- ")
            ]
            if len(content_bullets) < len(authority_bullets):
                return True

        if len(authority_content) == 1 and len(content_meaningful) == 0:
            return True

    return False

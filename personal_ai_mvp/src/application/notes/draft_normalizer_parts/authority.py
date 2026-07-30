"""Authority and house-style normalization helpers for generated notes."""

from __future__ import annotations

import re


def apply_authority_constraints(
    text: str,
    *,
    authoritative_text: str,
    grounded_tokens: set[str],
) -> str:
    del grounded_tokens
    authority_labels = extract_authority_labels(authoritative_text)
    if not authority_labels:
        return text

    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        bullet_match = re.match(r"^(\s*-\s+)([^:]+):\s+(.+)$", line)
        if bullet_match:
            prefix, raw_label, detail = bullet_match.groups()
            del detail
            normalized_label = normalize_label(raw_label)
            if normalized_label in authority_labels:
                cleaned_lines.append(f"{prefix}{raw_label.strip()}")
                continue

        cleaned_lines.append(line if stripped else "")

    return "\n".join(cleaned_lines)


def apply_template_constraints(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    if not authoritative_text.strip():
        return text

    lines = text.splitlines()
    lines = normalize_heading_variants(lines, authoritative_text)
    lines = preserve_labeled_bullet_blocks(lines, authoritative_text)
    return "\n".join(lines)


def normalize_house_style(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    lines = [strip_bullet_emphasis(line) for line in text.splitlines()]
    lines = normalize_bullet_case(lines, authoritative_text)
    return "\n".join(lines)


def extract_authority_label_map(text: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        label = stripped[2:].strip()
        if not label:
            continue
        labels[normalize_label(label)] = label
    return labels


def extract_authority_labels(text: str) -> set[str]:
    return set(extract_authority_label_map(text))


def normalize_label(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def normalize_heading_variants(lines: list[str], authoritative_text: str) -> list[str]:
    authority_headings = extract_headings(authoritative_text)
    if not authority_headings:
        return lines

    normalized_map = {
        normalize_heading_text(heading): heading
        for heading in authority_headings
    }

    updated: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            updated.append(line)
            continue

        prefix = stripped[: len(stripped) - len(stripped.lstrip("#"))]
        heading_text = stripped[len(prefix):].strip()
        replacement = best_matching_heading(heading_text, normalized_map)
        if replacement is None:
            updated.append(line)
            continue
        updated.append(f"{prefix} {replacement}")

    return updated


def preserve_labeled_bullet_blocks(lines: list[str], authoritative_text: str) -> list[str]:
    authority_labels_by_heading = extract_heading_labels(authoritative_text)
    if not authority_labels_by_heading:
        return lines

    result: list[str] = []
    current_heading: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("#"):
            current_heading = normalize_heading_text(stripped.lstrip("#").strip())
            result.append(line)
            index += 1
            continue

        labels = authority_labels_by_heading.get(current_heading or "")
        if not labels:
            result.append(line)
            index += 1
            continue

        if stripped and not stripped.startswith(("-", "#")):
            next_bullet = find_next_bullet_index(lines, index + 1)
            if next_bullet is not None:
                expected_label = next(iter(labels.values()))
                if not result or result[-1].strip() != expected_label:
                    result.append(expected_label)
                index = next_bullet
                continue

        result.append(line)
        index += 1

    return result


def extract_headings(text: str) -> list[str]:
    return [
        line.strip().lstrip("#").strip()
        for line in text.splitlines()
        if line.strip().startswith("#")
    ]


def extract_heading_labels(text: str) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    current_heading: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            current_heading = normalize_heading_text(stripped.lstrip("#").strip())
            mapping.setdefault(current_heading, {})
            continue
        if current_heading is None:
            continue
        if stripped.endswith(":") and not stripped.startswith("-"):
            mapping.setdefault(current_heading, {})[normalize_label(stripped[:-1])] = stripped
    return mapping


def normalize_heading_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def best_matching_heading(heading_text: str, normalized_map: dict[str, str]) -> str | None:
    normalized = normalize_heading_text(heading_text)
    if normalized in normalized_map:
        return normalized_map[normalized]

    numeric_prefix = re.match(r"^(\d+)\b", normalized)
    if numeric_prefix:
        numeric_heading = numeric_prefix.group(1)
        if numeric_heading in normalized_map:
            return normalized_map[numeric_heading]

    heading_tokens = set(normalized.split())
    best_match: tuple[float, str] | None = None
    for authority_normalized, authority_heading in normalized_map.items():
        authority_tokens = set(authority_normalized.split())
        if not heading_tokens or not authority_tokens:
            continue
        overlap = len(heading_tokens & authority_tokens) / len(heading_tokens | authority_tokens)
        if overlap < 0.5:
            continue
        candidate = (overlap, authority_heading)
        if best_match is None or candidate > best_match:
            best_match = candidate
    return best_match[1] if best_match is not None else None


def find_next_bullet_index(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            return index
        if stripped.startswith("#"):
            return None
    return None


def strip_bullet_emphasis(line: str) -> str:
    match = re.match(r"^(\s*-\s+)\*\*([^*]+)\*\*(.*)$", line)
    if not match:
        return line
    prefix, label, suffix = match.groups()
    return f"{prefix}{label}{suffix}"


def normalize_bullet_case(lines: list[str], authoritative_text: str) -> list[str]:
    authority_label_map = extract_authority_label_map(authoritative_text)
    if not authority_label_map:
        return lines

    updated: list[str] = []
    for line in lines:
        match = re.match(r"^(\s*-\s+)([^:]+)(.*)$", line)
        if not match:
            updated.append(line)
            continue

        prefix, raw_label, suffix = match.groups()
        normalized_label = normalize_label(raw_label)
        if normalized_label not in authority_label_map:
            updated.append(line)
            continue

        canonical = authority_label_map[normalized_label]
        updated.append(f"{prefix}{canonical}{suffix}")

    return updated


def re_collapse_authoritative_bullets(
    text: str,
    *,
    authoritative_text: str,
) -> str:
    authority_label_map = extract_authority_label_map(authoritative_text)
    if not authority_label_map:
        return text

    collapsed: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(\s*-\s+)([^:]+):\s+(.+)$", line)
        if not match:
            collapsed.append(line)
            continue

        prefix, raw_label, detail = match.groups()
        del detail
        normalized_label = normalize_label(raw_label)
        canonical = authority_label_map.get(normalized_label)
        if canonical is not None:
            collapsed.append(f"{prefix}{canonical}")
            continue

        collapsed.append(line)

    return "\n".join(collapsed)

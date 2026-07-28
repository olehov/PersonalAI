"""Small frontmatter parser for common Obsidian note metadata."""

from __future__ import annotations


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    """Parses top-level YAML-like frontmatter and returns metadata plus body."""
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    closing_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, text

    metadata = _parse_metadata_lines(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return metadata, body


def _parse_metadata_lines(lines: list[str]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_key is not None:
            current_value = metadata.setdefault(current_key, [])
            if isinstance(current_value, list):
                current_value.append(_coerce_value(stripped[2:].strip()))
            continue

        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        current_key = key

        if not value:
            metadata[key] = []
            continue

        metadata[key] = _coerce_value(value)

    return metadata


def _coerce_value(value: str) -> object:
    lowered = value.casefold()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if value.isdigit():
        return int(value)

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    return value


__all__ = [
    "parse_frontmatter",
]

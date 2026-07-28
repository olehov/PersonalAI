"""Scaffold parsing and validation helpers for agent runtime actions."""

from __future__ import annotations

import re
from pathlib import Path

from application.agent_runtime.action_support import (
    runtime_scaffold_dir_name,
    scaffold_path,
)
from application.agent_runtime.executor_prompting import (
    strip_markdown_fences,
)


def normalize_manifest_file_item(item: object) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    raw_path = item.get("path")
    raw_purpose = item.get("purpose", "")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    purpose = raw_purpose.strip() if isinstance(raw_purpose, str) else ""
    group = item.get("group", "")
    normalized_group = group.strip() if isinstance(group, str) else ""
    return {
        "path": raw_path.strip(),
        "purpose": purpose,
        "group": normalized_group,
    }


def parse_scaffold_tree_manifest(content: str) -> tuple[list[str], list[dict[str, str]]] | None:
    import json

    stripped = strip_markdown_fences(content)
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    raw_dirs = payload.get("dirs", [])
    raw_files = payload.get("files", [])
    raw_root_files = payload.get("root_files", [])
    raw_include_files = payload.get("include_files", [])
    raw_source_groups = payload.get("source_groups", [])
    if not isinstance(raw_dirs, list):
        return None

    dirs: list[str] = []
    for item in raw_dirs:
        if isinstance(item, str) and item.strip():
            dirs.append(item.strip())

    files: list[dict[str, str]] = []
    if isinstance(raw_files, list):
        for item in raw_files:
            normalized = normalize_manifest_file_item(item)
            if normalized is not None:
                files.append(normalized)
    if isinstance(raw_root_files, list):
        for item in raw_root_files:
            normalized = normalize_manifest_file_item(item)
            if normalized is not None:
                files.append(normalized)
    if isinstance(raw_include_files, list):
        for item in raw_include_files:
            normalized = normalize_manifest_file_item(item)
            if normalized is not None:
                files.append(normalized)
    if isinstance(raw_source_groups, list):
        for group in raw_source_groups:
            if not isinstance(group, dict):
                continue
            raw_group_name = group.get("name", "")
            group_name = raw_group_name.strip() if isinstance(raw_group_name, str) else ""
            raw_group_dir = group.get("dir")
            if isinstance(raw_group_dir, str) and raw_group_dir.strip():
                dirs.append(raw_group_dir.strip())
            raw_group_files = group.get("files", [])
            if not isinstance(raw_group_files, list):
                continue
            for item in raw_group_files:
                normalized = normalize_manifest_file_item(item)
                if normalized is None:
                    continue
                if group_name and not normalized["group"]:
                    normalized["group"] = group_name
                files.append(normalized)
    if not files and not dirs:
        return None
    return dirs, files


def dedupe_scaffold_tree_manifest(
    dirs: list[str],
    files: list[dict[str, str]],
) -> tuple[list[str], list[dict[str, str]]]:
    unique_dirs: list[str] = []
    seen_dirs: set[str] = set()
    for path in dirs:
        normalized = path.replace("\\", "/").strip()
        if not normalized or normalized in seen_dirs:
            continue
        seen_dirs.add(normalized)
        unique_dirs.append(normalized)

    unique_files: list[dict[str, str]] = []
    seen_files: set[str] = set()
    for item in files:
        path = item["path"].replace("\\", "/").strip()
        if not path or path in seen_files:
            continue
        seen_files.add(path)
        unique_files.append(
            {
                "path": path,
                "purpose": item.get("purpose", "").strip(),
                "group": item.get("group", "").strip(),
            }
        )
    return unique_dirs, unique_files


def build_scaffold_context_for_file(
    *,
    file_item: dict[str, str],
    all_files: list[dict[str, str]],
) -> str:
    lines = [
        f"target_group={file_item.get('group', '') or 'none'}",
        f"target_purpose={file_item.get('purpose', '') or 'none'}",
    ]
    sibling_paths = [
        candidate["path"]
        for candidate in all_files
        if candidate["path"] != file_item["path"]
        and candidate.get("group", "") == file_item.get("group", "")
    ]
    if sibling_paths:
        lines.append(f"group_siblings={'; '.join(sibling_paths)}")
    related_headers = [
        candidate["path"]
        for candidate in all_files
        if candidate["path"].endswith(".h")
    ]
    if related_headers:
        lines.append(f"declared_headers={'; '.join(related_headers)}")
    related_sources = [
        candidate["path"]
        for candidate in all_files
        if candidate["path"].endswith(".c")
    ]
    if related_sources:
        lines.append(f"declared_sources={'; '.join(related_sources)}")
    return "\n".join(lines)


def looks_like_bad_scaffold_output(
    *,
    content: str,
    target: str,
    request_text: str,
    expected_scaffold_paths: set[str] | None = None,
) -> bool:
    lowered = content.casefold()
    lowered_target = target.casefold()
    lowered_request = request_text.casefold()
    suffix = Path(target).suffix.casefold()
    target_name = Path(target).name
    if not lowered:
        return True
    if "```" in content:
        return True
    if suffix in {".c", ".h"} and any(
        token in lowered for token in ("from __future__", "def main", "import ", "class ")
    ):
        return True
    if target_name == "Makefile" and any(
        token in lowered for token in ("from __future__", "def main", "import ", "class ")
    ):
        return True
    if suffix == ".py" and any(
        token in lowered for token in ("#include <", "int main(", "printf(")
    ):
        return True
    if "helper" in lowered_request or "helper" in lowered_target:
        banned_tokens = (
            "import unittest",
            "from unittest",
            "tempfile",
            "redirect_stdout",
            "from cli_app.entry import main",
            "class clitests",
            "def test_",
            "pytest",
            "if __name__ ==",
            "argparse",
        )
        if any(token in lowered for token in banned_tokens):
            return True
        if "class " in lowered:
            return True
        if "def " not in lowered:
            return True
    if suffix == ".c" and Path(target).name != "main.c" and "int main(" in lowered:
        return True
    if expected_scaffold_paths and has_missing_scaffold_dependencies(
        content=content,
        target=target,
        expected_scaffold_paths=expected_scaffold_paths,
    ):
        return True
    if len(content.splitlines()) > 80:
        return True
    return False


def extract_local_c_includes(content: str) -> tuple[str, ...]:
    includes = re.findall(r'^\s*#include\s+"([^"]+)"', content, flags=re.MULTILINE)
    normalized: list[str] = []
    for include in includes:
        value = include.strip().replace("\\", "/")
        if value:
            normalized.append(value)
    return tuple(normalized)


def candidate_dependency_paths(target: str, include_name: str) -> tuple[str, ...]:
    target_path = Path(target)
    include_path = Path(include_name)
    include_value = include_path.as_posix()
    candidates = {include_value}
    if "include/" not in include_value:
        candidates.add(scaffold_path("include", include_value))
    candidates.add((target_path.parent / include_path).as_posix())
    candidates.add((Path(runtime_scaffold_dir_name()) / include_path).as_posix())
    return tuple(candidates)


def has_missing_scaffold_dependencies(
    *,
    content: str,
    target: str,
    expected_scaffold_paths: set[str],
) -> bool:
    suffix = Path(target).suffix.casefold()
    if suffix not in {".c", ".h"}:
        return False
    for include_name in extract_local_c_includes(content):
        candidates = candidate_dependency_paths(target, include_name)
        if any(candidate in expected_scaffold_paths for candidate in candidates):
            continue
        return True
    return False


__all__ = [
    "build_scaffold_context_for_file",
    "dedupe_scaffold_tree_manifest",
    "looks_like_bad_scaffold_output",
    "normalize_manifest_file_item",
    "parse_scaffold_tree_manifest",
]

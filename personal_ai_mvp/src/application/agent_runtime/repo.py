"""Compatibility facade for agent-runtime repository inspection helpers."""

from __future__ import annotations

from application.agent_runtime.repo_support.file_filters import (
    is_excluded_repo_context_file,
    is_preferred_repo_context_file,
)
from application.agent_runtime.repo_support.manifests import (
    build_config_summary,
    build_validation_plan,
    detect_test_framework_hints,
    extract_manifest_summary,
    extract_summary_values,
    flatten_toml_sections,
    inspect_repo_summary,
    recommend_validation_commands,
    summarize_makefile,
    summarize_package_json,
    summarize_pyproject,
)
from application.agent_runtime.repo_support.target_files import (
    canonicalize_repo_path_hint,
    collect_target_file_snippets,
    read_file_snippet,
    score_target_file_candidate,
    select_target_file_paths,
)
from application.agent_runtime.repo_support.tree import (
    build_file_tree_summary,
    collect_tree_lines,
    find_repo_files,
    find_repo_files_by_name,
)

__all__ = [
    "build_config_summary",
    "build_file_tree_summary",
    "build_validation_plan",
    "canonicalize_repo_path_hint",
    "collect_target_file_snippets",
    "collect_tree_lines",
    "detect_test_framework_hints",
    "extract_manifest_summary",
    "extract_summary_values",
    "find_repo_files",
    "find_repo_files_by_name",
    "flatten_toml_sections",
    "inspect_repo_summary",
    "is_excluded_repo_context_file",
    "is_preferred_repo_context_file",
    "read_file_snippet",
    "recommend_validation_commands",
    "score_target_file_candidate",
    "select_target_file_paths",
    "summarize_makefile",
    "summarize_package_json",
    "summarize_pyproject",
]

"""Safe execution adapters for agent runtime actions."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

from personal_ai.application.agent_tool_registry import AgentToolContext
from personal_ai.domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    PromptMessage,
)

MODULE_DRAFT_SYSTEM_PROMPT = (
    "You produce safe first-slice code drafts for a local engineering agent. "
    "Do not claim that files were created or edited. "
    "Return only a grounded draft artifact that can later be reviewed or applied."
)

PATCH_PLAN_SYSTEM_PROMPT = (
    "You produce safe patch plans for a local engineering agent. "
    "Do not claim that files were changed. "
    "Return only a reviewable patch plan artifact."
)

SCAFFOLD_FILE_SYSTEM_PROMPT = (
    "You produce one safe starter source file for a local engineering agent. "
    "Return only the raw file contents with no markdown fences, no explanation, and no claims about execution. "
    "Keep the scaffold minimal, syntactically plausible, and aligned to the requested path and repository context."
)

SCAFFOLD_TREE_SYSTEM_PROMPT = (
    "You produce a safe scaffold-tree manifest for a local engineering agent. "
    "Return only compact JSON with two arrays: dirs and files. "
    "Each dir must be a relative path under runtime_scaffold. "
    "Each file item must be an object with path and purpose fields, and path must be relative under runtime_scaffold. "
    "Do not include markdown fences, commentary, or claims about execution."
)

_RESTRICTED_REPO_SEGMENTS = {
    ".git",
    ".runtime",
    ".venv",
    ".venv-unsloth",
    "node_modules",
    ".personal_ai",
    "__pycache__",
}


def _slugify_target(target: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", target.strip())
    sanitized = sanitized.strip("-._")
    return sanitized or "artifact"


def _persist_artifact_draft(
    *,
    vault_root: Path,
    resolved_repo_path: Path | None,
    kind: str,
    target: str,
    content: str,
) -> str | None:
    drafts_root = vault_root / ".personal_ai" / "agent_runtime_drafts"
    repo_segment = (
        resolved_repo_path.relative_to(vault_root).as_posix().replace("/", "__")
        if resolved_repo_path is not None
        else "no_repo"
    )
    output_dir = drafts_root / repo_segment
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{kind}__{_slugify_target(target)}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path.relative_to(vault_root).as_posix()


def _resolve_allowed_command(
    command: str,
) -> list[str] | None:
    stripped = command.strip()
    if not stripped:
        return None
    if stripped.startswith("python -m "):
        suffix = stripped[len("python -m ") :].strip()
        if not suffix:
            return None
        return [sys.executable, "-m", *suffix.split()]
    if stripped.startswith("npm run "):
        npm_path = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm_path:
            return None
        script = stripped[len("npm run ") :].strip()
        if not script:
            return None
        return [npm_path, "run", *script.split()]
    if stripped.startswith("make"):
        make_path = shutil.which("make")
        if not make_path:
            return None
        parts = stripped.split()
        return [make_path, *parts[1:]]
    return None


def _resolve_safe_repo_write_path(
    *,
    resolved_repo_path: Path | None,
    target: str,
) -> tuple[Path | None, str | None]:
    if resolved_repo_path is None:
        return None, "Safe write actions need a resolved repository path."
    normalized = target.replace("\\", "/").strip()
    if not normalized:
        return None, "Safe write target was empty."
    candidate = Path(normalized)
    if candidate.is_absolute():
        return None, "Absolute paths are not allowed for safe repo writes."
    if any(part in {"..", ""} for part in candidate.parts):
        return None, "Parent-directory traversal is not allowed for safe repo writes."
    if any(part.casefold() in _RESTRICTED_REPO_SEGMENTS for part in candidate.parts):
        return None, "Safe repo writes cannot target restricted runtime or environment directories."
    resolved_path = (resolved_repo_path / candidate).resolve()
    try:
        resolved_path.relative_to(resolved_repo_path.resolve())
    except ValueError:
        return None, "Resolved write target escaped the selected repository scope."
    return resolved_path, None


def _build_probe_file_content(
    *,
    repo_display_path: str,
    target: str,
    request_text: str,
    instruction: str,
) -> str:
    return "\n".join(
        [
            "# Runtime Write Probe",
            "",
            "created_by=safe_agent_runtime",
            f"repo={repo_display_path}",
            f"target={target}",
            f"request={request_text}",
            f"instruction={instruction}",
            "",
            "This file was created by the controlled create_file runtime adapter.",
        ]
    )


def _build_scaffold_file_prompt(
    *,
    repo_display_path: str,
    target: str,
    request_text: str,
    instruction: str,
    build_config_summary: str | None,
    target_file_snippets: dict[str, str],
    scaffold_context: str | None = None,
) -> str:
    lowered_request = request_text.casefold()
    lowered_target = target.casefold()
    role_hints: list[str] = []
    if "helper" in lowered_request or "helper" in lowered_target:
        role_hints.extend(
            [
                "- This target is a helper module, not a test file and not a CLI entrypoint.",
                "- Prefer one or two small pure helper functions over classes or command parsing.",
                "- Do not import unittest, tempfile, redirect_stdout, or test-only helpers.",
                "- Do not copy existing test modules or CLI wiring into the scaffold.",
            ]
        )
    if lowered_target.endswith(".py"):
        role_hints.extend(
            [
                "- Use Python source code only.",
                "- Include only imports that the scaffold actually needs.",
            ]
        )
    context_lines = [
        "Scaffold File Contract:",
        "- Return only the file contents.",
        "- Do not use markdown fences.",
        "- Do not claim the file was executed or imported.",
        "- Keep the scaffold compact and reviewable.",
        "- Prefer the repository's existing style when the target file context is relevant.",
        *role_hints,
        "",
        f"Repo: {repo_display_path}",
        f"Target Path: {target}",
        f"Request: {request_text}",
        f"Instruction: {instruction}",
        "",
        "Build Config:",
        build_config_summary or "none",
        "",
        "Scaffold Context:",
        scaffold_context or "none",
        "",
        "Target File Context:",
    ]
    if target_file_snippets:
        for path, snippet in target_file_snippets.items():
            context_lines.append(f"path={path}")
            context_lines.append(snippet)
            context_lines.append("")
    else:
        context_lines.append("none")
    return "\n".join(context_lines).strip()


def _build_scaffold_tree_prompt(
    *,
    repo_display_path: str,
    request_text: str,
    instruction: str,
    build_config_summary: str | None,
    target_file_snippets: dict[str, str],
) -> str:
    context_lines = [
        "Scaffold Tree Contract:",
        "- Return JSON only.",
        '- Preferred schema: {"dirs": [...], "root_files": [{"path": "...", "purpose": "..."}], "include_files": [{"path": "...", "purpose": "..."}], "source_groups": [{"name": "...", "dir": "runtime_scaffold/...", "files": [{"path": "...", "purpose": "..."}]}]}',
        '- Legacy schema is also accepted: {"dirs": [...], "files": [{"path": "...", "purpose": "..."}]}',
        "- Every path must stay under runtime_scaffold.",
        "- Prefer a realistic modular project tree over a single-file scaffold when the request implies a medium or large project.",
        "- Keep the tree reviewable and implementation-oriented.",
        "- Do not include test/framework artifacts unless the request strongly implies them.",
        "- Do not include files outside runtime_scaffold.",
        "- Include shared headers, root entrypoints, and build files when the project shape implies them.",
        "- Do not invent isolated leaf modules with dependencies on files that are missing from the same scaffold tree.",
        "- If one file includes or imports another project-local file, that companion file must also appear in the manifest.",
        "- For C projects, prefer include_files plus source_groups such as parser, executor, builtins, and signals.",
        "",
        f"Repo: {repo_display_path}",
        f"Request: {request_text}",
        f"Instruction: {instruction}",
        "",
        "Build Config:",
        build_config_summary or "none",
        "",
        "Target File Context:",
    ]
    if target_file_snippets:
        for path, snippet in target_file_snippets.items():
            context_lines.append(f"path={path}")
            context_lines.append(snippet)
            context_lines.append("")
    else:
        context_lines.append("none")
    return "\n".join(context_lines).strip()


def _fallback_scaffold_file_content(target: str) -> str:
    target_name = Path(target).name
    suffix = Path(target).suffix.casefold()
    if target_name == "Makefile":
        return "\n".join(
            [
                "NAME := scaffold_app",
                "CC := cc",
                "CFLAGS := -Wall -Wextra -Werror",
                "",
                "SRC := src/main.c",
                "OBJ := $(SRC:.c=.o)",
                "",
                "all: $(NAME)",
                "",
                "$(NAME): $(OBJ)",
                "\t$(CC) $(CFLAGS) $(OBJ) -o $(NAME)",
                "",
                "clean:",
                "\trm -f $(OBJ)",
                "",
                "fclean: clean",
                "\trm -f $(NAME)",
                "",
                "re: fclean all",
            ]
        )
    if suffix == ".py":
        stem = Path(target).stem
        if "helper" in stem.casefold():
            return "\n".join(
                [
                    '"""Generated helper scaffold."""',
                    "",
                    "from __future__ import annotations",
                    "",
                    "",
                    "def normalize_text(value: str) -> str:",
                    '    """Return a trimmed single-line representation."""',
                    '    return " ".join(value.strip().split())',
                ]
            )
        return "\n".join(
            [
                '"""Generated scaffold file."""',
                "",
                "from __future__ import annotations",
                "",
                "",
                "def main() -> int:",
                '    """Return a success code for the scaffold entrypoint."""',
                "    return 0",
                "",
                "",
                'if __name__ == "__main__":',
                "    raise SystemExit(main())",
            ]
        )
    if suffix in {".js", ".mjs"}:
        return "\n".join(
            [
                "/** Generated scaffold file. */",
                "",
                "export function main() {",
                "  return 0;",
                "}",
            ]
        )
    if suffix in {".c", ".h"}:
        if suffix == ".h":
            return "\n".join(
                [
                    "/* Generated scaffold header. */",
                    "#ifndef GENERATED_SCAFFOLD_H",
                    "#define GENERATED_SCAFFOLD_H",
                    "",
                    "int generated_scaffold(void);",
                    "",
                    "#endif",
                ]
            )
        return "\n".join(
            [
                "/* Generated scaffold file. */",
                "",
                "int generated_scaffold(void)",
                "{",
                "    return 0;",
                "}",
            ]
        )
    return "\n".join(
        [
            "# Generated Scaffold",
            "",
            "created_by=safe_agent_runtime",
            f"target={target}",
        ]
    )


def _strip_markdown_fences(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _normalize_manifest_file_item(item: object) -> dict[str, str] | None:
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


def _parse_scaffold_tree_manifest(content: str) -> tuple[list[str], list[dict[str, str]]] | None:
    import json

    stripped = _strip_markdown_fences(content)
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
            normalized = _normalize_manifest_file_item(item)
            if normalized is not None:
                files.append(normalized)
    if isinstance(raw_root_files, list):
        for item in raw_root_files:
            normalized = _normalize_manifest_file_item(item)
            if normalized is not None:
                files.append(normalized)
    if isinstance(raw_include_files, list):
        for item in raw_include_files:
            normalized = _normalize_manifest_file_item(item)
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
                normalized = _normalize_manifest_file_item(item)
                if normalized is None:
                    continue
                if group_name and not normalized["group"]:
                    normalized["group"] = group_name
                files.append(normalized)
    if not files and not dirs:
        return None
    return dirs, files


def _is_runtime_scaffold_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip().strip("/")
    return normalized == "runtime_scaffold" or normalized.startswith("runtime_scaffold/")


def _manifest_has_only_runtime_scaffold_paths(
    dirs: list[str],
    files: list[dict[str, str]],
) -> bool:
    if any(not _is_runtime_scaffold_path(path) for path in dirs):
        return False
    if any(not _is_runtime_scaffold_path(item["path"]) for item in files):
        return False
    return True


def _fallback_scaffold_tree_manifest(request_text: str) -> tuple[list[str], list[dict[str, str]]]:
    lowered = request_text.casefold()
    if "minishell" in lowered or " shell" in lowered or lowered.endswith("shell"):
        return (
            [
                "runtime_scaffold/include",
                "runtime_scaffold/src",
                "runtime_scaffold/src/builtins",
                "runtime_scaffold/src/executor",
                "runtime_scaffold/src/lexer",
                "runtime_scaffold/src/parser",
                "runtime_scaffold/src/signals",
            ],
            [
                {"path": "runtime_scaffold/Makefile", "purpose": "Build the minishell target from modular C sources."},
                {"path": "runtime_scaffold/include/minishell.h", "purpose": "Shared core shell structures and lifecycle prototypes."},
                {"path": "runtime_scaffold/include/parser.h", "purpose": "Parser and token interfaces."},
                {"path": "runtime_scaffold/include/executor.h", "purpose": "Pipeline and command execution interfaces."},
                {"path": "runtime_scaffold/include/builtins.h", "purpose": "Builtin dispatch interfaces."},
                {"path": "runtime_scaffold/include/signals.h", "purpose": "Interactive signal handling interfaces."},
                {"path": "runtime_scaffold/src/main.c", "purpose": "Program entrypoint and shell loop wiring."},
                {"path": "runtime_scaffold/src/shell.c", "purpose": "Read-eval loop and high-level orchestration."},
                {"path": "runtime_scaffold/src/parser/lexer.c", "purpose": "Token scanning for shell input."},
                {"path": "runtime_scaffold/src/parser/parser.c", "purpose": "Command and pipeline parsing."},
                {"path": "runtime_scaffold/src/executor/exec.c", "purpose": "PATH resolution and execve-based external execution."},
                {"path": "runtime_scaffold/src/executor/redirections.c", "purpose": "Input/output redirection helpers."},
                {"path": "runtime_scaffold/src/executor/pipes.c", "purpose": "Pipeline creation and fd wiring."},
                {"path": "runtime_scaffold/src/builtins/builtins.c", "purpose": "Builtin dispatch table and implementations."},
                {"path": "runtime_scaffold/src/signals/interactive.c", "purpose": "Interactive ctrl-C and ctrl-\\ behavior."},
            ],
        )
    if any(token in lowered for token in ("python", "pyproject", "cli")):
        return (
            [
                "runtime_scaffold/src",
                "runtime_scaffold/src/app",
                "runtime_scaffold/tests",
            ],
            [
                {"path": "runtime_scaffold/pyproject.toml", "purpose": "Python project metadata and test configuration."},
                {"path": "runtime_scaffold/src/app/__init__.py", "purpose": "Package marker."},
                {"path": "runtime_scaffold/src/app/main.py", "purpose": "CLI or application entrypoint."},
                {"path": "runtime_scaffold/src/app/helpers.py", "purpose": "Reusable helper functions for the first slice."},
                {"path": "runtime_scaffold/tests/test_basic.py", "purpose": "Minimal regression test scaffold."},
            ],
        )
    if any(token in lowered for token in ("javascript", "typescript", "node", "react", "vite", "frontend")):
        return (
            [
                "runtime_scaffold/src",
                "runtime_scaffold/public",
            ],
            [
                {"path": "runtime_scaffold/package.json", "purpose": "Project scripts and package metadata."},
                {"path": "runtime_scaffold/src/main.js", "purpose": "Application bootstrap entrypoint."},
                {"path": "runtime_scaffold/src/helpers.js", "purpose": "Reusable helper module for the first slice."},
            ],
        )
    return (
        ["runtime_scaffold/src"],
        [
            {"path": "runtime_scaffold/src/main.txt", "purpose": "Starter scaffold artifact for the requested project."},
        ],
    )


def _dedupe_scaffold_tree_manifest(
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


def _build_scaffold_context_for_file(
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


def _looks_like_bad_scaffold_output(
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
            "from personal_ai.cli import main",
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
    if expected_scaffold_paths and _has_missing_scaffold_dependencies(
        content=content,
        target=target,
        expected_scaffold_paths=expected_scaffold_paths,
    ):
        return True
    if len(content.splitlines()) > 80:
        return True
    return False


def _extract_local_c_includes(content: str) -> tuple[str, ...]:
    includes = re.findall(r'^\s*#include\s+"([^"]+)"', content, flags=re.MULTILINE)
    normalized: list[str] = []
    for include in includes:
        value = include.strip().replace("\\", "/")
        if value:
            normalized.append(value)
    return tuple(normalized)


def _candidate_dependency_paths(target: str, include_name: str) -> tuple[str, ...]:
    target_path = Path(target)
    include_path = Path(include_name)
    include_value = include_path.as_posix()
    candidates = {include_value}
    if "include/" not in include_value:
        candidates.add(f"runtime_scaffold/include/{include_value}")
    candidates.add((target_path.parent / include_path).as_posix())
    candidates.add((Path("runtime_scaffold") / include_path).as_posix())
    return tuple(candidates)


def _has_missing_scaffold_dependencies(
    *,
    content: str,
    target: str,
    expected_scaffold_paths: set[str],
) -> bool:
    suffix = Path(target).suffix.casefold()
    if suffix not in {".c", ".h"}:
        return False
    for include_name in _extract_local_c_includes(content):
        candidates = _candidate_dependency_paths(target, include_name)
        if any(candidate in expected_scaffold_paths for candidate in candidates):
            continue
        return True
    return False


def execute_inspect_note(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    compact_excerpt,
) -> AgentRuntimeActionExecution:
    note = context.retrieval_notes.get(action.target)
    if note is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="failed",
            output_text="Grounded note was not available in the retrieved context bundle.",
        )
    excerpt = compact_excerpt(note.content)
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"title={note.title}\n"
            f"path={note.path.as_posix()}\n"
            f"link_count={len(note.links)}\n"
            f"excerpt={excerpt}"
        ),
    )


def execute_inspect_repo(
    action: AgentRuntimeAction,
    context: AgentToolContext,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="failed",
            output_text="Could not resolve a grounded repository path from the current request and scope.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status="executed",
        output_text=repo_summary["summary"],
    )


def execute_plan_validation(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    build_validation_plan,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Validation planning needs a resolved project directory before concrete commands can be proposed.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status="executed",
        output_text=build_validation_plan(
            repo_summary,
            context.build_config_summary,
        ),
    )


def execute_inspect_file_tree(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    vault_root: Path,
    build_file_tree_summary,
) -> AgentRuntimeActionExecution:
    resolved_repo_path = context.resolved_repo_path
    if resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="File-tree inspection needs a resolved repository path before it can enumerate project files.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=resolved_repo_path.relative_to(vault_root).as_posix(),
        status="executed",
        output_text=build_file_tree_summary(resolved_repo_path),
    )


def execute_inspect_build_config(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    vault_root: Path,
    build_config_summary,
) -> AgentRuntimeActionExecution:
    resolved_repo_path = context.resolved_repo_path
    if resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Build-config inspection needs a resolved repository path before it can inspect manifests.",
        )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=resolved_repo_path.relative_to(vault_root).as_posix(),
        status="executed",
        output_text=context.build_config_summary
        or build_config_summary(resolved_repo_path),
    )


def execute_inspect_target_files(
    action: AgentRuntimeAction,
    context: AgentToolContext,
) -> AgentRuntimeActionExecution:
    if not context.target_file_snippets:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                "Target-file inspection needs a resolved repository path and at least one concrete file hint from the planner or repo scan."
            ),
        )
    preview_lines: list[str] = []
    for path, snippet in context.target_file_snippets.items():
        preview_lines.append(f"path={path}")
        preview_lines.append(snippet)
        preview_lines.append("")
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text="\n".join(preview_lines).strip(),
    )


def execute_draft_module(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    vault_root: Path,
    build_module_draft_prompt,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Module drafting needs a resolved repository path and repo summary before a grounded draft can be produced.",
        )

    prompt = build_module_draft_prompt(action, context)
    draft_text = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=MODULE_DRAFT_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    )
    saved_path = _persist_artifact_draft(
        vault_root=vault_root,
        resolved_repo_path=context.resolved_repo_path,
        kind="module_draft",
        target=action.target,
        content=draft_text,
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"saved_path={saved_path}\n\n{draft_text}"
            if saved_path is not None
            else draft_text
        ),
    )


def execute_plan_patch(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    vault_root: Path,
    build_patch_plan_prompt,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Patch planning needs a resolved repository path and repo summary before a grounded patch plan can be produced.",
        )
    prompt = build_patch_plan_prompt(action, context)
    patch_plan_text = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=PATCH_PLAN_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    )
    saved_path = _persist_artifact_draft(
        vault_root=vault_root,
        resolved_repo_path=context.resolved_repo_path,
        kind="patch_plan",
        target=action.target,
        content=patch_plan_text,
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"saved_path={saved_path}\n\n{patch_plan_text}"
            if saved_path is not None
            else patch_plan_text
        ),
    )


def execute_run_allowed_command(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    recommend_validation_commands,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    resolved_repo_path = context.resolved_repo_path
    if repo_summary is None or resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Command execution needs a resolved repository path and validation baseline.",
        )
    recommended = recommend_validation_commands(
        repo_summary=repo_summary,
        build_config_summary=context.build_config_summary,
    )
    if not recommended:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=repo_summary["display_path"],
            status="deferred",
            output_text="No safe validation command was inferred from the current repository markers.",
        )
    attempts: list[str] = []
    final_status = "failed"
    output_lines: list[str] = []
    for index, selected in enumerate(recommended, start=1):
        argv = _resolve_allowed_command(selected)
        if argv is None:
            attempts.append(
                "\n".join(
                    [
                        f"attempt={index}",
                        f"command={selected}",
                        "status=deferred",
                        "reason=Validation command is not in the safe whitelist or the executable is unavailable.",
                    ]
                )
            )
            continue
        try:
            completed = subprocess.run(
                argv,
                cwd=resolved_repo_path,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            attempts.append(
                "\n".join(
                    [
                        f"attempt={index}",
                        f"command={selected}",
                        "status=failed",
                        f"error={exc}",
                    ]
                )
            )
            continue

        stdout_preview = (completed.stdout or "").strip()
        stderr_preview = (completed.stderr or "").strip()
        attempt_lines = [
            f"attempt={index}",
            f"command={selected}",
            f"cwd={repo_summary['display_path']}",
            f"exit_code={completed.returncode}",
        ]
        if stdout_preview:
            attempt_lines.append(f"stdout={stdout_preview[:1600]}")
        if stderr_preview:
            attempt_lines.append(f"stderr={stderr_preview[:1600]}")
        attempts.append("\n".join(attempt_lines))
        if completed.returncode == 0:
            final_status = "executed"
            output_lines = attempt_lines
            break

    if not output_lines:
        output_lines = ["All recommended validation commands failed or were unavailable.", *attempts]
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=repo_summary["display_path"],
        status=final_status,
        output_text="\n".join(output_lines),
    )


def execute_create_dir(
    action: AgentRuntimeAction,
    context: AgentToolContext,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    target_path, error = _resolve_safe_repo_write_path(
        resolved_repo_path=context.resolved_repo_path,
        target=action.target,
    )
    if repo_summary is None or target_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=error or "Could not resolve a safe repository directory target.",
        )
    if target_path.exists():
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                f"Directory already exists and was left unchanged: "
                f"{target_path.relative_to(context.resolved_repo_path).as_posix()}"
            ),
        )
    target_path.mkdir(parents=True, exist_ok=False)
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"created_dir={target_path.relative_to(context.resolved_repo_path).as_posix()}\n"
            f"repo={repo_summary['display_path']}"
        ),
    )


def execute_create_file(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    action_generation_options,
    scaffold_context: str | None = None,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    target_path, error = _resolve_safe_repo_write_path(
        resolved_repo_path=context.resolved_repo_path,
        target=action.target,
    )
    if repo_summary is None or target_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=error or "Could not resolve a safe repository file target.",
        )
    if target_path.exists():
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text=(
                f"File already exists and was left unchanged: "
                f"{target_path.relative_to(context.resolved_repo_path).as_posix()}"
            ),
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lowered_instruction = action.instruction.casefold()
    if "probe" in lowered_instruction:
        file_content = _build_probe_file_content(
            repo_display_path=repo_summary["display_path"],
            target=action.target,
            request_text=context.request_text,
            instruction=action.instruction,
        )
    else:
        prompt = _build_scaffold_file_prompt(
            repo_display_path=repo_summary["display_path"],
            target=action.target,
            request_text=context.request_text,
            instruction=action.instruction,
            build_config_summary=context.build_config_summary,
            target_file_snippets=context.target_file_snippets,
            scaffold_context=scaffold_context,
        )
        generated = ollama_client.chat_with_options(
            model=context.model,
            messages=(
                PromptMessage(role="system", content=SCAFFOLD_FILE_SYSTEM_PROMPT),
                PromptMessage(role="user", content=prompt),
            ),
            options=action_generation_options(context.model),
        ).strip()
        generated = _strip_markdown_fences(generated)
        if _looks_like_bad_scaffold_output(
            content=generated,
            target=action.target,
            request_text=context.request_text,
            expected_scaffold_paths=None,
        ):
            file_content = _fallback_scaffold_file_content(action.target)
        else:
            file_content = generated
    target_path.write_text(
        file_content,
        encoding="utf-8",
    )
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status="executed",
        output_text=(
            f"created_file={target_path.relative_to(context.resolved_repo_path).as_posix()}\n"
            f"repo={repo_summary['display_path']}"
        ),
    )


def execute_create_scaffold_tree(
    action: AgentRuntimeAction,
    context: AgentToolContext,
    *,
    ollama_client,
    action_generation_options,
) -> AgentRuntimeActionExecution:
    repo_summary = context.repo_summary
    if repo_summary is None or context.resolved_repo_path is None:
        return AgentRuntimeActionExecution(
            action_type=action.action_type,
            target=action.target,
            status="deferred",
            output_text="Scaffold-tree creation needs a resolved repository path before safe writes can be applied.",
        )

    prompt = _build_scaffold_tree_prompt(
        repo_display_path=repo_summary["display_path"],
        request_text=context.request_text,
        instruction=action.instruction,
        build_config_summary=context.build_config_summary,
        target_file_snippets=context.target_file_snippets,
    )
    generated = ollama_client.chat_with_options(
        model=context.model,
        messages=(
            PromptMessage(role="system", content=SCAFFOLD_TREE_SYSTEM_PROMPT),
            PromptMessage(role="user", content=prompt),
        ),
        options=action_generation_options(context.model),
    ).strip()
    parsed = _parse_scaffold_tree_manifest(generated)
    if parsed is None:
        dirs, files = _fallback_scaffold_tree_manifest(context.request_text)
    else:
        dirs, files = parsed
    if not _manifest_has_only_runtime_scaffold_paths(dirs, files):
        dirs, files = _fallback_scaffold_tree_manifest(context.request_text)
    dirs, files = _dedupe_scaffold_tree_manifest(dirs, files)

    created_dirs: list[str] = []
    created_files: list[str] = []
    skipped: list[str] = []

    for directory in dirs:
        execution = execute_create_dir(
            AgentRuntimeAction(
                action_type="create_dir",
                title=f"Create {directory}",
                target=directory,
                instruction=action.instruction,
                rationale=action.rationale,
            ),
            context,
        )
        if execution.status == "executed":
            created_dirs.append(directory)
        else:
            skipped.append(f"dir:{directory}:{execution.status}")

    for item in files:
        file_path = item["path"]
        file_instruction = (
            f"{action.instruction}\n\nRequested scaffold file purpose: {item['purpose']}"
            if item["purpose"]
            else action.instruction
        )
        execution = execute_create_file(
            AgentRuntimeAction(
                action_type="create_file",
                title=f"Create {file_path}",
                target=file_path,
                instruction=file_instruction,
                rationale=action.rationale,
            ),
            context,
            ollama_client=ollama_client,
            action_generation_options=action_generation_options,
            scaffold_context=_build_scaffold_context_for_file(
                file_item=item,
                all_files=files,
            ),
        )
        if execution.status == "executed":
            created_files.append(file_path)
        else:
            skipped.append(f"file:{file_path}:{execution.status}")

    expected_scaffold_paths = {path for path in created_files}
    for file_path in created_files:
        resolved_path, error = _resolve_safe_repo_write_path(
            resolved_repo_path=context.resolved_repo_path,
            target=file_path,
        )
        if resolved_path is None or error is not None or not resolved_path.is_file():
            continue
        content = resolved_path.read_text(encoding="utf-8")
        if _looks_like_bad_scaffold_output(
            content=content,
            target=file_path,
            request_text=context.request_text,
            expected_scaffold_paths=expected_scaffold_paths,
        ):
            resolved_path.write_text(
                _fallback_scaffold_file_content(file_path),
                encoding="utf-8",
            )
            skipped.append(f"repaired:{file_path}:fallback")

    if created_dirs or created_files:
        status = "executed"
    elif skipped:
        status = "deferred"
    else:
        status = "failed"

    lines = [
        f"repo={repo_summary['display_path']}",
        f"created_dir_count={len(created_dirs)}",
        f"created_file_count={len(created_files)}",
    ]
    if created_dirs:
        lines.append(f"created_dirs={'; '.join(created_dirs)}")
    if created_files:
        lines.append(f"created_files={'; '.join(created_files)}")
    if skipped:
        lines.append(f"skipped={'; '.join(skipped)}")
    return AgentRuntimeActionExecution(
        action_type=action.action_type,
        target=action.target,
        status=status,
        output_text="\n".join(lines),
    )

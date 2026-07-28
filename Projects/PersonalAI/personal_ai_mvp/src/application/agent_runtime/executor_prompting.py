"""Prompt construction helpers for executor-stage runtime actions."""

from __future__ import annotations

from application.agent_runtime.instruction_set import (
    build_executor_approval_review_prompt,
)


def build_scaffold_file_prompt(
    *,
    repo_display_path: str,
    target: str,
    request_text: str,
    instruction: str,
    build_config_summary: str | None,
    target_file_snippets: dict[str, str],
    scaffold_context: str | None = None,
) -> str:
    """Build the scaffold-file generation prompt."""
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


def build_scaffold_tree_prompt(
    *,
    repo_display_path: str,
    request_text: str,
    instruction: str,
    build_config_summary: str | None,
    target_file_snippets: dict[str, str],
    scaffold_root_dir_name: str,
) -> str:
    """Build the scaffold-tree generation prompt."""
    context_lines = [
        "Scaffold Tree Contract:",
        "- Return JSON only.",
        f'- Preferred schema: {{"dirs": [...], "root_files": [{{"path": "...", "purpose": "..."}}], "include_files": [{{"path": "...", "purpose": "..."}}], "source_groups": [{{"name": "...", "dir": "{scaffold_root_dir_name}/...", "files": [{{"path": "...", "purpose": "..."}}]}}]}}',
        '- Legacy schema is also accepted: {"dirs": [...], "files": [{"path": "...", "purpose": "..."}]}',
        f"- Every path must stay under {scaffold_root_dir_name}.",
        "- Prefer a realistic modular project tree over a single-file scaffold when the request implies a medium or large project.",
        "- Keep the tree reviewable and implementation-oriented.",
        "- Do not include test/framework artifacts unless the request strongly implies them.",
        f"- Do not include files outside {scaffold_root_dir_name}.",
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


def strip_markdown_fences(content: str) -> str:
    """Remove one outer fenced-code wrapper when the model returns markdown."""
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


def build_executor_critique_prompt(
    *,
    artifact_kind: str,
    request_text: str,
    instruction: str,
    draft_text: str,
) -> str:
    """Build the executor critique prompt."""
    return "\n".join(
        [
            "Executor Artifact Critique:",
            f"Artifact Kind: {artifact_kind}",
            f"Request: {request_text}",
            f"Instruction: {instruction}",
            "",
            "Draft Artifact:",
            draft_text,
            "",
            "Return short bullets for:",
            "- missing grounding",
            "- unsafe or misleading claims",
            "- structural weaknesses",
            "- the best concrete improvement",
        ]
    )


def build_executor_refinement_prompt(
    *,
    artifact_kind: str,
    request_text: str,
    instruction: str,
    draft_text: str,
    critique_text: str,
) -> str:
    """Build the executor refinement prompt."""
    return "\n".join(
        [
            "Executor Artifact Final Pass:",
            f"Artifact Kind: {artifact_kind}",
            f"Request: {request_text}",
            f"Instruction: {instruction}",
            "",
            "Original Draft:",
            draft_text,
            "",
            "Critique:",
            critique_text,
            "",
            "Return the improved final artifact only.",
        ]
    )


def build_executor_approver_prompt(
    *,
    artifact_kind: str,
    request_text: str,
    instruction: str,
    draft_text: str,
) -> str:
    """Build the executor approval-review prompt."""
    return build_executor_approval_review_prompt(
        artifact_kind=artifact_kind,
        request_text=request_text,
        instruction=instruction,
        draft_text=draft_text,
    )

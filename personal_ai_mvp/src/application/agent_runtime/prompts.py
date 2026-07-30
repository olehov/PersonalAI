"""Pure prompt and formatting helpers for the agent runtime."""

from __future__ import annotations

import re
from pathlib import Path

from application.agent_runtime.instruction_set import (
    HIGH_REASONING_MODE_SUFFIX,
    MODULE_DRAFT_CONTRACT,
    PATCH_PLAN_CONTRACT,
    PLANNING_CONTRACT,
)

def parse_planning_sections(planning_output: str) -> dict[str, str]:
    """Split the planning output into top-level titled sections."""
    headings = (
        "Goal",
        "Constraints",
        "Existing Context",
        "Modules",
        "Incremental Slices",
        "First Slice",
        "First Actions",
        "Validation",
        "Runtime Limits",
    )
    pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?P<title>"
        + "|".join(re.escape(item) for item in headings)
        + r")\s*:?\s*$",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(planning_output))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group("title").casefold()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(planning_output)
        sections[title] = planning_output[start:end].strip()
    return sections


def extract_plan_lines(section_text: str) -> list[str]:
    """Normalize numbered or bulleted planning lines into compact entries."""
    lines: list[str] = []
    for raw_line in section_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        normalized = re.sub(r"^(?:[-*]\s+|\d+[.)]\s+)", "", stripped).strip()
        if not normalized:
            continue
        lines.append(normalized)
    return lines


def build_system_prompt(system_prompt: str, reasoning_mode: str) -> str:
    """Return the system prompt tuned for the requested reasoning mode."""
    if reasoning_mode != "high":
        return system_prompt
    return f"{system_prompt} {HIGH_REASONING_MODE_SUFFIX}"


def build_planning_prompt(
    *,
    request_text: str,
    normalized_goal: str,
    answer_prompt: str,
    retrieval_observation: str,
    reasoning_mode: str,
    repo_summary_text: str = "none",
    file_tree_summary: str = "none",
    build_config_summary: str = "none",
    suggested_files: str = "- none",
    target_file_context: str = "- none",
) -> str:
    """Build the planning-stage user prompt."""
    return (
        f"{PLANNING_CONTRACT}\n\n"
        f"Normalized Goal:\n{normalized_goal}\n\n"
        f"Task Brief:\n{_extract_task_brief(answer_prompt)}\n\n"
        f"Reasoning Mode:\n{reasoning_mode}\n\n"
        f"Retrieval Observation:\n{retrieval_observation}\n\n"
        f"Repo Summary:\n{repo_summary_text}\n\n"
        f"File Tree:\n{file_tree_summary}\n\n"
        f"Build Config:\n{build_config_summary}\n\n"
        f"Suggested Files:\n{suggested_files}\n\n"
        f"Target File Context:\n{target_file_context}\n\n"
        f"Original Request:\n{request_text.strip()}"
    )


def _extract_task_brief(answer_prompt: str) -> str:
    """Collapse the upstream answer prompt into a compact planning brief."""
    wanted_labels = {
        "Question:",
        "Task Mode:",
        "Primary Notes:",
        "Related Notes:",
    }
    kept_lines: list[str] = []
    keep_block = False
    for raw_line in answer_prompt.splitlines():
        stripped = raw_line.rstrip()
        if not stripped:
            continue
        if any(stripped.startswith(label) for label in wanted_labels):
            keep_block = True
            kept_lines.append(stripped)
            continue
        if re.match(r"^[A-Za-z][A-Za-z ]+:\s*$", stripped) and stripped not in wanted_labels:
            keep_block = False
        if keep_block:
            kept_lines.append(stripped)
    if kept_lines:
        return "\n".join(kept_lines)
    return compact_excerpt(answer_prompt, limit=1400)


def sanitize_planning_artifact(content: str) -> str:
    """Strip meta chatter and keep only the planning artifact body."""
    headings = (
        "Goal",
        "Constraints",
        "Existing Context",
        "Modules",
        "Incremental Slices",
        "First Slice",
        "First Actions",
        "Validation",
        "Runtime Limits",
    )
    pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?:APPROVED|NEEDS_REVISION)?\s*$|^\s*(?:#{1,6}\s*)?(?P<title>"
        + "|".join(re.escape(item) for item in headings)
        + r")\s*:?\s*$",
        flags=re.MULTILINE,
    )
    title_pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?P<title>"
        + "|".join(re.escape(item) for item in headings)
        + r")\s*:?\s*$",
        flags=re.MULTILINE,
    )
    matches = list(title_pattern.finditer(content))
    if matches:
        return content[matches[0].start() :].strip()
    stripped = content.strip()
    stripped = re.sub(r"^(?:APPROVED|NEEDS_REVISION)\s*", "", stripped, count=1, flags=re.IGNORECASE)
    return stripped


def sanitize_structured_artifact(
    content: str,
    *,
    headings: tuple[str, ...],
) -> str:
    """Trim executor artifacts down to the first recognized heading block."""
    if not content.strip():
        return content.strip()
    pattern = re.compile(
        r"^\s*(?:#{1,6}\s*)?(?P<title>"
        + "|".join(re.escape(item) for item in headings)
        + r")\s*:?\s*$",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(content))
    if matches:
        return content[matches[0].start() :].strip()
    stripped = content.strip()
    stripped = re.sub(r"^(?:APPROVED|NEEDS_REVISION)\s*", "", stripped, count=1, flags=re.IGNORECASE)
    return stripped


def build_structured_plan_fallback_from_prompt(prompt_text: str) -> str:
    """Build a deterministic planning artifact when the model returns malformed output."""
    def _extract_prompt_block(label: str) -> str:
        pattern = re.compile(
            rf"{re.escape(label)}:\n(?P<body>.*?)(?:\n[A-Z][A-Za-z ]+:\n|\Z)",
            flags=re.DOTALL,
        )
        match = pattern.search(prompt_text)
        return match.group("body").strip() if match else ""

    def _extract_suggested_files() -> list[str]:
        block = _extract_prompt_block("Suggested Files")
        files: list[str] = []
        for raw_line in block.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("- "):
                candidate = stripped[2:].strip()
                if candidate and candidate.lower() != "none":
                    files.append(candidate)
        return files

    goal = _extract_prompt_block("Normalized Goal") or "Complete the requested first implementation slice."
    files = _extract_suggested_files()
    build_config = _extract_prompt_block("Build Config")
    repo_summary = _extract_prompt_block("Repo Summary")
    first_file = files[0] if files else "the primary implementation file from the inspected repository"
    second_file = files[1] if len(files) > 1 else None
    goal_lower = goal.casefold()
    if any(token in goal_lower for token in ("parser", "token", "quote", "pipe", "redirect")):
        modules_lines = files[:4] or [
            "parser/tokenizer implementation file",
            "command data-structure header",
        ]
        first_slice = (
            f"Implement the tokenizer/parser entrypoint in {first_file}, keeping the slice limited to "
            "token boundaries, quote state tracking, and recognition of pipe/redirection operators."
        )
        first_actions = [
            f"Edit {first_file} to add a token scanner that walks the input character by character and emits tokens for words, pipes, and redirections.",
        ]
        if second_file is not None:
            first_actions.append(
                f"Update {second_file} only if declarations or token/command structs are required for the new parser entrypoint."
            )
        first_actions.append(
            "Keep unmatched-quote detection and parse errors explicit, but defer full execution wiring to a later slice."
        )
        incremental_slices = [
            "Implement token scanning and quote-state handling in the primary parser file.",
            "Introduce command/pipeline structs and map token streams into command segments.",
            "Wire redirection metadata and then connect the parser output to execution flow.",
        ]
    else:
        modules_lines = files[:4] or ["existing implementation file", "adjacent declaration/config file"]
        first_slice = (
            f"Implement the narrowest code-facing first slice in {first_file}, and touch only one adjacent file if declarations or wiring are required."
        )
        first_actions = [f"Edit {first_file} for the smallest safe implementation change that advances the requested goal."]
        if second_file is not None:
            first_actions.append(f"Update {second_file} only if the first file requires matching declarations or minimal wiring.")
        first_actions.append("Defer wider refactors, new subsystems, and follow-on validation until the first slice is reviewable.")
        incremental_slices = [
            "Land the smallest code-facing first slice in the primary target file.",
            "Wire the adjacent declarations or callers needed to make the first slice coherent.",
            "Run the first safe validation command and expand scope only after that baseline is stable.",
        ]

    validation_lines: list[str] = []
    build_config_lower = build_config.casefold()
    if "make" in build_config_lower:
        validation_lines.append("Run `make all` as the first build check.")
    elif "pytest" in build_config_lower:
        validation_lines.append("Run `python -m pytest` as the first validation pass.")
    elif "unittest" in build_config_lower:
        validation_lines.append("Run `python -m unittest discover -s tests` as the first validation pass.")
    elif "npm" in build_config_lower:
        validation_lines.append("Run the first repository-defined npm validation command.")
    else:
        validation_lines.append("Inspect the repository build/test entrypoint and run only the first safe validation command.")
    validation_lines.append("Confirm the first-slice symbols, files, and declarations match the existing repository structure.")

    existing_context_lines = []
    if repo_summary:
        existing_context_lines.append(f"- Repo summary: {repo_summary.splitlines()[0]}")
    if build_config:
        existing_context_lines.append(f"- Build config: {build_config.splitlines()[0]}")
    if files:
        existing_context_lines.append("- Suggested files: " + ", ".join(files[:4]))
    if not existing_context_lines:
        existing_context_lines.append("- Use the inspected repository tree and file excerpts as the grounding baseline.")

    lines = [
        "Goal",
        goal,
        "",
        "Constraints",
        "- Keep scope limited to the first implementation slice.",
        "- Do not claim files were changed or tests were run in this planning artifact.",
        "- Reuse the existing repository structure before proposing any new file.",
        "",
        "Existing Context",
        *existing_context_lines,
        "",
        "Modules",
        *[f"- {item}" for item in modules_lines],
        "",
        "Incremental Slices",
        *[f"{index}. {item}" for index, item in enumerate(incremental_slices, start=1)],
        "",
        "First Slice",
        first_slice,
        "",
        "First Actions",
        *[f"{index}. {item}" for index, item in enumerate(first_actions, start=1)],
        "",
        "Validation",
        *[f"{index}. {item}" for index, item in enumerate(validation_lines, start=1)],
        "",
        "Runtime Limits",
        "This run produced a planning artifact only; it did not mutate files, execute shell commands, or run tests.",
    ]
    return "\n".join(lines).strip()


def build_retrieval_observation(answer_bundle) -> str:
    """Summarize retrieved grounded context for the planning stage."""
    retrieval = answer_bundle.retrieval
    primary_count = len(retrieval.primary_notes)
    related_count = len(retrieval.related_notes)
    citations = ", ".join(answer_bundle.citations) if answer_bundle.citations else "none"
    return (
        f"Retrieved {primary_count} primary notes and {related_count} related notes. "
        f"Task mode: {answer_bundle.task_mode}. "
        f"Citations: {citations}."
    )


def summarize_retrieval(answer_bundle) -> str:
    """Render a compact retrieval summary for runtime artifacts."""
    lines = [
        f"question={answer_bundle.question}",
        f"task_mode={answer_bundle.task_mode}",
    ]
    if answer_bundle.citations:
        lines.append("citations=" + ", ".join(answer_bundle.citations))
    else:
        lines.append("citations=none")
    return "\n".join(lines)


def build_planner_handoff(
    planning_output: str,
    *,
    resolved_repo_path: Path | None,
    filter_repo_like_paths,
) -> str:
    """Extract a compact executor handoff from the planning artifact."""
    sections = parse_planning_sections(planning_output)
    if not sections:
        return (
            "chosen_first_slice=none\n"
            "why_this_slice=none\n"
            "target_files=none\n"
            "must_not_do=do not invent repository facts"
        )

    first_slice = sections.get("first slice", "").strip() or "none"
    first_actions = extract_plan_lines(sections.get("first actions", ""))
    validation = extract_plan_lines(sections.get("validation", ""))
    combined_text = "\n".join(
        (
            sections.get("modules", ""),
            sections.get("first slice", ""),
            sections.get("first actions", ""),
        )
    )
    target_files = filter_repo_like_paths(
        combined_text,
        resolved_repo_path=resolved_repo_path,
        files_only=True,
    )
    why_this_slice = (
        first_actions[0]
        if first_actions
        else "Use the safest narrow slice that reuses the current repository structure."
    )
    lines = [
        f"chosen_first_slice={first_slice}",
        f"why_this_slice={why_this_slice}",
        "target_files=" + (", ".join(target_files) if target_files else "none"),
        (
            "must_not_do=do not claim files were changed or tests were run; "
            "do not invent new repository structure when existing modules already fit"
        ),
    ]
    if validation:
        lines.append("validation_targets=" + "; ".join(validation))
    return "\n".join(lines)


def compact_excerpt(content: str, *, limit: int = 220) -> str:
    """Collapse multi-line text into one bounded excerpt."""
    collapsed = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def build_target_file_context(context: AgentToolContext) -> str:
    """Render collected target-file snippets for prompts."""
    if not context.target_file_snippets:
        return "- none"
    blocks: list[str] = []
    for path, snippet in context.target_file_snippets.items():
        blocks.append(f"- {path}\n{snippet}")
    return "\n\n".join(blocks)


def render_target_file_context(target_file_snippets: dict[str, str]) -> str:
    """Render collected target-file snippets without requiring a full tool context."""
    if not target_file_snippets:
        return "- none"
    blocks: list[str] = []
    for path, snippet in target_file_snippets.items():
        blocks.append(f"- {path}\n{snippet}")
    return "\n\n".join(blocks)


def build_validation_baseline(
    context: AgentToolContext,
    *,
    build_validation_plan,
) -> str:
    """Render the execution baseline for later validation."""
    if context.repo_summary is None:
        return "recommended_commands=inspect existing build/test entrypoints before execution"
    return build_validation_plan(
        context.repo_summary,
        context.build_config_summary,
    )


def build_module_draft_prompt(
    *,
    context: AgentToolContext,
    action_title: str,
    action_target: str,
    action_instruction: str,
    repo_summary_text: str,
    file_tree_summary: str,
    build_config_summary: str,
    suggested_files: str,
    related_files: str,
    edit_bundle: str,
    target_file_context: str,
    validation_baseline: str,
    planner_handoff: str,
    notes_block: str,
    citations: str,
) -> str:
    """Build the module-draft prompt sent to the executor model."""
    return (
        f"{MODULE_DRAFT_CONTRACT}\n\n"
        f"Normalized Goal:\n{context.normalized_goal}\n\n"
        f"Original Request:\n{context.request_text.strip()}\n\n"
        f"Action:\n{action_title}\n"
        f"Target:\n{action_target}\n"
        f"Instruction:\n{action_instruction}\n\n"
        f"Repo Summary:\n{repo_summary_text}\n\n"
        f"File Tree:\n{file_tree_summary}\n\n"
        f"Build Config:\n{build_config_summary}\n\n"
        f"Suggested Files:\n{suggested_files}\n\n"
        f"Related Files:\n{related_files}\n\n"
        f"Edit Bundle:\n{edit_bundle}\n\n"
        f"Target File Context:\n{target_file_context}\n\n"
        f"Validation Baseline:\n{validation_baseline}\n\n"
        f"Planner Handoff:\n{planner_handoff}\n\n"
        f"Relevant Notes:\n{notes_block}\n\n"
        f"Citations:\n{citations}\n\n"
        f"Planning Output:\n{context.planning_output}"
    )


def build_patch_plan_prompt(
    *,
    context: AgentToolContext,
    action_title: str,
    action_target: str,
    action_instruction: str,
    repo_summary_text: str,
    file_tree_summary: str,
    build_config_summary: str,
    suggested_files: str,
    related_files: str,
    edit_bundle: str,
    target_file_context: str,
    validation_baseline: str,
    planner_handoff: str,
    notes_block: str,
    citations: str,
) -> str:
    """Build the patch-plan prompt sent to the executor model."""
    return (
        f"{PATCH_PLAN_CONTRACT}\n\n"
        f"Normalized Goal:\n{context.normalized_goal}\n\n"
        f"Original Request:\n{context.request_text.strip()}\n\n"
        f"Action:\n{action_title}\n"
        f"Target:\n{action_target}\n"
        f"Instruction:\n{action_instruction}\n\n"
        f"Repo Summary:\n{repo_summary_text}\n\n"
        f"File Tree:\n{file_tree_summary}\n\n"
        f"Build Config:\n{build_config_summary}\n\n"
        f"Suggested Files:\n{suggested_files}\n\n"
        f"Related Files:\n{related_files}\n\n"
        f"Edit Bundle:\n{edit_bundle}\n\n"
        f"Target File Context:\n{target_file_context}\n\n"
        f"Validation Baseline:\n{validation_baseline}\n\n"
        f"Planner Handoff:\n{planner_handoff}\n\n"
        f"Relevant Notes:\n{notes_block}\n\n"
        f"Citations:\n{citations}\n\n"
        f"Planning Output:\n{context.planning_output}"
    )

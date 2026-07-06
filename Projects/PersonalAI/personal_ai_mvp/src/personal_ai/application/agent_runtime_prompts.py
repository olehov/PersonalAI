"""Pure prompt and formatting helpers for the agent runtime."""

from __future__ import annotations

import re
from pathlib import Path

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
    return (
        f"{system_prompt} "
        "High reasoning mode is enabled: spend extra effort selecting the most leverage-heavy first slice, "
        "challenge weak plans, and make hidden assumptions explicit."
    )


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
        f"{answer_prompt}\n\n"
        "Agent Runtime Contract:\n"
        "- Treat this as a project-scale coding task.\n"
        "- Do not pretend to execute files, tests, compilers, or shell commands.\n"
        "- Produce an implementation-ready first slice that a future execution runtime can carry out.\n"
        "- Use exactly these top-level sections in this order: Goal, Constraints, Existing Context, Modules, Incremental Slices, First Slice, First Actions, Validation, Runtime Limits.\n"
        "- Under Modules, name concrete files, functions, services, or subsystems.\n"
        "- Under Incremental Slices, break the task into 3 to 6 ordered slices.\n"
        "- Under First Slice, define the safest first deliverable that can be implemented without pretending the whole project is done.\n"
        "- Under First Actions, list exact edits, commands, or checks that a future execution agent should perform.\n"
        "- Under Validation, list the first concrete tests or checks to run.\n"
        "- Compare possible first slices internally and choose one; do not output a vague menu of equally weighted options.\n"
        "- Prefer the slice that reduces uncertainty fastest while keeping scope narrow and reviewable.\n"
        "- When the repository already appears known enough from the request or retrieved notes, choose a small real implementation change rather than an analysis-only step.\n"
        "- Do not choose 'inspect', 'read', 'review', or 'analyze' as the only First Slice deliverable when a concrete code-facing slice is already possible.\n"
        "- The First Slice should usually name a concrete file and a real code change such as adding a function, wiring a CLI command, or updating persistence logic.\n"
        "- First Actions should start with concrete file edits, not only observation steps, unless the request is genuinely too ambiguous to modify code safely.\n"
        "- Treat Repo Summary, File Tree, Suggested Files, and Target File Context as the authoritative source of current repository structure.\n"
        "- Prefer extending existing files from the inspected tree before proposing any new file.\n"
        "- If you propose a new file, mark it explicitly as a new file and justify why an existing file from Suggested Files is not sufficient.\n"
        "- Do not invent modules, paths, or filenames that conflict with the inspected repository tree.\n"
        "- State critical assumptions where they materially affect the first slice or validation path.\n"
        "- Under Runtime Limits, explicitly state that this run produced a plan artifact only and did not mutate files.\n\n"
        f"Reasoning Mode:\n{reasoning_mode}\n\n"
        f"Normalized Goal:\n{normalized_goal}\n\n"
        f"Retrieval Observation:\n{retrieval_observation}\n\n"
        f"Repo Summary:\n{repo_summary_text}\n\n"
        f"File Tree:\n{file_tree_summary}\n\n"
        f"Build Config:\n{build_config_summary}\n\n"
        f"Suggested Files:\n{suggested_files}\n\n"
        f"Target File Context:\n{target_file_context}\n\n"
        f"Original Request:\n{request_text.strip()}"
    )


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
    target_file_context: str,
    validation_baseline: str,
    planner_handoff: str,
    notes_block: str,
    citations: str,
) -> str:
    """Build the module-draft prompt sent to the executor model."""
    return (
        "Module Draft Contract:\n"
        "- Produce a safe first-slice module draft only.\n"
        "- Do not claim that files were changed on disk.\n"
        "- Use exactly these top-level sections in this order: Target, Intent, Suggested Files, Draft, Integration Notes, Validation Notes.\n"
        "- Under Draft, provide a compact code skeleton or file scaffold that fits the first slice.\n"
        "- Follow the Planner Handoff when it names a concrete first slice or target files.\n"
        "- Reuse the existing repository structure instead of inventing a new architecture.\n"
        "- Prefer editing an existing module over creating a new placeholder API when the file tree already shows a likely integration point.\n"
        "- If the repository already separates CLI logic, storage, parsing, or execution, preserve that split and describe the real data flow.\n"
        "- Do not return placeholder-only code unless the chosen first slice is explicitly a scaffold.\n"
        "- Treat Target File Context, Suggested Files, and Related Files as the authoritative source of real repository structure and current code.\n"
        "- If the Planning Output conflicts with the real file excerpts, follow the real file excerpts and mention the inconsistency instead of inventing a new structure.\n"
        "- Validation Notes must align with the supplied build config and validation baseline.\n"
        "- Keep the draft grounded in the supplied repo summary, file tree, build config, and note context.\n\n"
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
    validation_baseline: str,
    notes_block: str,
    citations: str,
) -> str:
    """Build the patch-plan prompt sent to the executor model."""
    return (
        "Patch Planning Contract:\n"
        "- Produce a safe patch plan only.\n"
        "- Do not claim files were edited, created, or tested.\n"
        "- Use exactly these top-level sections in this order: Scope, Files, Edits, Risks, Validation Order.\n"
        "- Under Files, list concrete repository-relative paths.\n"
        "- Under Edits, describe intended changes per file in short actionable bullets.\n"
        "- Keep the plan limited to the first implementation slice.\n"
        "- Prefer the real file excerpts and resolved repository paths over any conflicting free-form planning text.\n\n"
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
        f"Validation Baseline:\n{validation_baseline}\n\n"
        f"Relevant Notes:\n{notes_block}\n\n"
        f"Citations:\n{citations}\n\n"
        f"Planning Output:\n{context.planning_output}"
    )

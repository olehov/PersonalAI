"""Planning and action-list helpers for the agent runtime."""

from __future__ import annotations

from personal_ai.application.query_mapping import normalize_knowledge_query
from personal_ai.domain.models import (
    AgentRuntimeAction,
    AgentRuntimeActionExecution,
    AgentRuntimeTaskPlan,
    AgentRuntimeTaskPlanEntry,
    PromptMessage,
)


def build_task_plan(
    *,
    normalized_goal: str,
    planning_output: str,
    recommended_actions: tuple[AgentRuntimeAction, ...],
    parse_planning_sections,
    extract_plan_lines,
) -> AgentRuntimeTaskPlan | None:
    """Extract a structured task plan from the free-form planning artifact."""
    sections = parse_planning_sections(planning_output)
    if not sections:
        return None

    goal = sections.get("goal", normalized_goal).strip() or normalized_goal
    current_focus = sections.get("first slice", "").strip()
    if not current_focus:
        current_focus = sections.get("first actions", "").strip()
    if not current_focus:
        current_focus = "Start with the first grounded implementation slice."

    entries: list[AgentRuntimeTaskPlanEntry] = []
    next_index = 1
    for title in extract_plan_lines(sections.get("incremental slices", "")):
        entries.append(
            AgentRuntimeTaskPlanEntry(
                step_index=next_index,
                title=title,
                status="next" if next_index == 1 else "pending",
                details=title,
                source_section="Incremental Slices",
            )
        )
        next_index += 1

    if not entries:
        for title in extract_plan_lines(sections.get("first actions", "")):
            entries.append(
                AgentRuntimeTaskPlanEntry(
                    step_index=next_index,
                    title=title,
                    status="next" if next_index == 1 else "pending",
                    details=title,
                    source_section="First Actions",
                )
            )
            next_index += 1

    if not entries:
        for action in recommended_actions[:4]:
            entries.append(
                AgentRuntimeTaskPlanEntry(
                    step_index=next_index,
                    title=action.title,
                    status="next" if next_index == 1 else "pending",
                    details=action.instruction,
                    source_section="Recommended Actions",
                )
            )
            next_index += 1

    summary = (
        f"{len(entries)} planned implementation tasks. "
        "Retrieval and planning are complete; execution is still pending."
    )
    validation_checks = tuple(extract_plan_lines(sections.get("validation", "")))
    return AgentRuntimeTaskPlan(
        goal=goal,
        current_focus=current_focus,
        summary=summary,
        entries=tuple(entries),
        validation_checks=validation_checks,
    )


def build_recursive_critique_messages(
    *,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
) -> tuple[PromptMessage, ...]:
    """Ask the model to critique a planning draft before finalizing it."""
    critique_prompt = (
        "Recursive Planning Critique:\n"
        "- Audit the draft plan against the grounded retrieval and the runtime contract.\n"
        "- Focus on correctness, grounding, missing implementation detail, weak first-slice choice, invented repository facts, and vague validation steps.\n"
        "- Return exactly these sections in this order: Strengths, Issues, Missing Grounding, Better First Slice, Improve.\n"
        "- Keep it short and concrete.\n\n"
        f"Draft Plan:\n{draft_text}"
    )
    return (
        *base_messages,
        PromptMessage(role="assistant", content=draft_text),
        PromptMessage(role="user", content=critique_prompt),
    )


def build_recursive_refinement_messages(
    *,
    base_messages: tuple[PromptMessage, ...],
    draft_text: str,
    critique_text: str,
) -> tuple[PromptMessage, ...]:
    """Ask the model to rewrite the planning output after critique."""
    refinement_prompt = (
        "Recursive Planning Final Pass:\n"
        "- Rewrite the planning output using the critique.\n"
        "- Keep the exact top-level section order required by the runtime contract.\n"
        "- Prefer concrete files, modules, actions, and validation commands.\n"
        "- Remove invented repository facts, fake execution claims, and generic filler.\n"
        "- Return only the improved final planning artifact.\n\n"
        f"Initial Draft:\n{draft_text}\n\n"
        f"Critique:\n{critique_text}"
    )
    return (
        *base_messages,
        PromptMessage(role="assistant", content=draft_text),
        PromptMessage(role="user", content=refinement_prompt),
    )


def merge_conversation_history(
    *,
    base_messages: tuple[PromptMessage, ...],
    conversation_history: tuple[PromptMessage, ...],
    max_history_turns: int,
    max_history_chars_per_message: int,
) -> tuple[PromptMessage, ...]:
    """Insert recent user/assistant turns before the current runtime prompt."""
    if len(base_messages) < 2:
        return base_messages

    normalized_history = normalize_conversation_history(
        conversation_history=conversation_history,
        max_history_turns=max_history_turns,
        max_history_chars_per_message=max_history_chars_per_message,
    )
    if not normalized_history:
        return base_messages

    return (
        base_messages[0],
        *normalized_history,
        *base_messages[1:],
    )


def normalize_conversation_history(
    *,
    conversation_history: tuple[PromptMessage, ...],
    max_history_turns: int,
    max_history_chars_per_message: int,
) -> tuple[PromptMessage, ...]:
    """Keep only compact user/assistant turns relevant to the current chat."""
    normalized: list[PromptMessage] = []
    for message in conversation_history:
        role = message.role.strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = compact_history_content(
            message.content,
            max_history_chars_per_message=max_history_chars_per_message,
        )
        if not content:
            continue
        normalized.append(PromptMessage(role=role, content=content))

    if not normalized:
        return ()

    return tuple(normalized[-max_history_turns:])


def compact_history_content(
    content: str,
    *,
    max_history_chars_per_message: int,
) -> str:
    """Trim oversized conversation turns before sending them to the model."""
    stripped = content.strip()
    if not stripped:
        return ""
    if len(stripped) <= max_history_chars_per_message:
        return stripped
    return stripped[: max_history_chars_per_message - 3].rstrip() + "..."


def normalize_goal(request_text: str) -> str:
    stripped_lines = [line.strip() for line in request_text.splitlines() if line.strip()]
    for line in stripped_lines:
        lowered = line.casefold()
        if lowered.startswith("your task is to "):
            return normalize_knowledge_query(line)
        if "build the mandatory part" in lowered:
            return normalize_knowledge_query(line)
        if "implement the mandatory part" in lowered:
            return normalize_knowledge_query(line)
        if "write a shell" in lowered:
            return normalize_knowledge_query(line)
        if "minishell" in lowered:
            return normalize_knowledge_query(line)
    if stripped_lines:
        return normalize_knowledge_query(stripped_lines[0])
    return normalize_knowledge_query(request_text.strip())


def build_recommended_actions(
    *,
    normalized_goal: str,
    request_text: str,
    answer_bundle,
) -> tuple[AgentRuntimeAction, ...]:
    citations = answer_bundle.citations
    first_citation = citations[0] if citations else "(missing grounded note)"
    actions: list[AgentRuntimeAction] = [
        AgentRuntimeAction(
            action_type="inspect_note",
            title="Inspect Primary Knowledge Note",
            target=first_citation,
            instruction=(
                "Read the highest-priority grounded note and extract concrete modules, APIs, "
                "data flow, and constraints relevant to the first implementation slice."
            ),
            rationale="Execution should begin from the strongest grounded vault context, not from a blind code-generation jump.",
        ),
    ]

    lowered = f"{normalized_goal}\n{request_text}".casefold()
    requests_write_probe = "write probe" in lowered
    requests_scaffold_write = any(
        phrase in lowered
        for phrase in (
            "create file",
            "create files",
            "create folder",
            "create directory",
            "scaffold",
        )
    )
    if "minishell" in lowered or "shell" in lowered:
        actions.extend(
            (
                AgentRuntimeAction(
                    action_type="inspect_repo",
                    title="Inspect Current Minishell Project Layout",
                    target="current project workspace",
                    instruction=(
                        "List existing directories, source files, headers, build files, and entrypoints before proposing edits."
                    ),
                    rationale="Project-scale shell tasks need current repository state before scaffolding or refactoring decisions.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_file_tree",
                    title="Inspect Repository File Tree",
                    target="top-level source and header layout",
                    instruction=(
                        "Capture a compact file-tree view of the repository so the first implementation slice can reference real source, header, and test paths."
                    ),
                    rationale="A tree view reduces vague module drafts and helps anchor the next slice to actual files.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_build_config",
                    title="Inspect Build Configuration",
                    target="Makefile / build manifests",
                    instruction=(
                        "Read the primary build configuration files and summarize the active targets, scripts, or test entrypoints relevant to the first slice."
                    ),
                    rationale="Explicit build-config inspection makes later validation plans less heuristic and more grounded.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_target_files",
                    title="Inspect First Slice Target Files",
                    target="planner-selected implementation files",
                    instruction=(
                        "Read the concrete files implied by the first slice and capture compact code excerpts before drafting changes."
                    ),
                    rationale="Real file excerpts help the executor extend existing code instead of inventing a fresh module shape.",
                ),
                AgentRuntimeAction(
                    action_type="draft_module",
                    title="Draft Parser-Or-Loop First Slice",
                    target="src/parser.* or main loop entrypoint",
                    instruction=(
                        "Choose one safe first slice such as tokenization, parser scaffolding, or shell loop wiring, and limit edits to that slice."
                    ),
                    rationale="A narrow first slice reduces hallucinated project completion and makes later validation tractable.",
                ),
                AgentRuntimeAction(
                    action_type="plan_patch",
                    title="Plan Safe First Patch",
                    target="first implementation slice files",
                    instruction=(
                        "Propose a safe, reviewable patch plan with exact files, intended edits, and validation order for only the first implementation slice."
                    ),
                    rationale="A patch plan bridges high-level planning and future controlled execution without mutating files.",
                ),
            )
        )
    else:
        actions.extend(
            (
                AgentRuntimeAction(
                    action_type="inspect_repo",
                    title="Inspect Project Structure",
                    target="current project workspace",
                    instruction=(
                        "Discover existing modules, tests, and entrypoints before choosing the first implementation slice."
                    ),
                    rationale="Project-scale requests need repository context before code changes are safe.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_file_tree",
                    title="Inspect Repository File Tree",
                    target="top-level project files",
                    instruction=(
                        "Capture a compact file-tree view of the repository before selecting the first implementation slice."
                    ),
                    rationale="A file tree gives the planning runtime enough structural context to stay concrete.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_build_config",
                    title="Inspect Build Configuration",
                    target="project build manifests",
                    instruction=(
                        "Read the primary build or test manifests and summarize the concrete scripts or commands already present in the repository."
                    ),
                    rationale="Grounded build-config context helps the runtime propose validation steps it can justify.",
                ),
                AgentRuntimeAction(
                    action_type="inspect_target_files",
                    title="Inspect First Slice Target Files",
                    target="planner-selected implementation files",
                    instruction=(
                        "Read the concrete files implied by the first slice and capture compact code excerpts before drafting changes."
                    ),
                    rationale="Real file excerpts help the executor extend existing code instead of inventing a fresh module shape.",
                ),
                AgentRuntimeAction(
                    action_type="draft_module",
                    title="Draft First Implementation Slice",
                    target="first implementation slice module",
                    instruction=(
                        "Choose one narrow first slice from the real repository and draft only that module, function, or CLI entrypoint."
                    ),
                    rationale="A concrete first-slice draft is the clearest handoff from planner to executor for non-shell projects too.",
                ),
                AgentRuntimeAction(
                    action_type="plan_patch",
                    title="Plan Safe First Patch",
                    target="first implementation slice files",
                    instruction=(
                        "Propose a safe patch plan that identifies the first files to touch, the intended edits, and the first validation step."
                    ),
                    rationale="A structured patch plan keeps the runtime concrete while still remaining non-mutating.",
                ),
            )
        )

    if requests_write_probe:
        actions.extend(
            (
                AgentRuntimeAction(
                    action_type="create_dir",
                    title="Create Safe Scaffold Directory",
                    target="runtime_write_probe",
                    instruction=(
                        "Create one new repository-local scaffold directory for a controlled write-permission probe."
                    ),
                    rationale="A dedicated probe directory verifies safe write access without mutating existing source files.",
                ),
                AgentRuntimeAction(
                    action_type="create_file",
                    title="Create Safe Probe File",
                    target="runtime_write_probe/WRITE_PROBE.md",
                    instruction=(
                        "Create one new repository-local probe file inside the scaffold directory and record the request metadata."
                    ),
                    rationale="A new file proves controlled write capability while avoiding overwrite of real project files.",
                ),
            )
        )
    elif requests_scaffold_write:
        actions.extend(
            (
                AgentRuntimeAction(
                    action_type="create_scaffold_tree",
                    title="Create Safe Scaffold Tree",
                    target="runtime_scaffold",
                    instruction=(
                        "Create a reviewable repository-local scaffold tree with multiple directories and starter files that fit the requested project shape."
                    ),
                    rationale="A dedicated scaffold directory keeps the first generated file isolated from existing project files.",
                ),
            )
        )

    actions.append(
        AgentRuntimeAction(
            action_type="plan_validation",
            title="Prepare First Validation Pass",
            target="tests/build commands",
            instruction=(
                "Identify the first command, test, or static check that should run after the initial slice is implemented."
            ),
            rationale="A planning artifact is more useful when it ends with a concrete validation target.",
        )
    )
    actions.append(
        AgentRuntimeAction(
            action_type="run_allowed_command",
            title="Run First Safe Validation Command",
            target="first inferred validation command",
            instruction=(
                "Run only the first whitelist validation command inferred from the repository build markers and capture stdout, stderr, and exit code."
            ),
            rationale="A real validation signal reduces fake confidence and keeps the runtime anchored to executable project reality.",
        )
    )
    return tuple(actions)


def render_action_plan(actions: tuple[AgentRuntimeAction, ...]) -> str:
    lines: list[str] = []
    for index, action in enumerate(actions, start=1):
        lines.append(
            f"{index}. {action.action_type} | {action.title} | target={action.target}"
        )
        lines.append(f"   instruction: {action.instruction}")
        lines.append(f"   rationale: {action.rationale}")
    return "\n".join(lines)


def render_action_executions(
    executions: tuple[AgentRuntimeActionExecution, ...],
) -> str:
    lines: list[str] = []
    for index, execution in enumerate(executions, start=1):
        lines.append(
            f"{index}. {execution.action_type} | target={execution.target} | status={execution.status}"
        )
        lines.append(f"   output: {execution.output_text}")
    return "\n".join(lines)

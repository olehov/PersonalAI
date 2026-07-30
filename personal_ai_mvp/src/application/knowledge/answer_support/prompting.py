"""Prompt-building helpers for grounded answer preparation."""

from __future__ import annotations

from application.knowledge.answer_support.excerpting import (
    excerpt,
    indent_block,
)
from domain.models import RetrievalBundle, RetrievedNote

SYSTEM_PROMPT = (
    "You are PersonalAI, a local-first software engineering assistant focused first on writing code, "
    "explaining implementation details, and turning knowledge into actionable engineering output. "
    "Answer using only the supplied vault context when possible. "
    "If the context is incomplete, say what is missing instead of inventing details. "
    "Prefer code-first, implementation-first responses over high-level theory. "
    "When the user asks how to build something, start with concrete structure, APIs, algorithms, or code steps. "
    "Reason carefully before answering: reconcile conflicting notes, compare plausible implementation options, "
    "and choose the most defensible answer supported by the retrieved context. "
    "Before finalizing, internally check for unsupported claims, missing edge cases, and places where the request likely needs a narrower assumption. "
    "Keep answers concise, technical, and grounded, and cite note paths when making claims. "
    "Do not format the answer like an Obsidian note unless the user explicitly asks for note output. "
    "Prefer natural technical prose by default, using bullets or short sections only when they improve clarity."
)

HIGH_REASONING_APPENDIX = (
    "High Reasoning Mode:\n"
    "- Spend extra effort resolving ambiguity before answering.\n"
    "- Compare the strongest implementation options and reject weaker ones.\n"
    "- Surface hidden assumptions, edge cases, cleanup rules, and failure modes that could break a real implementation.\n"
    "- Prefer a precise, opinionated answer over a broad survey when the retrieved notes support a concrete choice."
)


def build_system_prompt(reasoning_mode: str) -> str:
    if reasoning_mode != "high":
        return SYSTEM_PROMPT
    return (
        f"{SYSTEM_PROMPT} "
        "Use a deeper reasoning pass for this request: validate the design choice against the retrieved notes, "
        "check likely failure paths, and avoid stopping at the first plausible answer."
    )


def build_user_prompt(retrieval: RetrievalBundle, task_mode: str, reasoning_mode: str) -> str:
    instructions = [
        "- Ground the answer in the provided notes.",
        "- Treat the user as asking for software implementation help first.",
        "- Start with code structure, function breakdown, data flow, or step-by-step implementation guidance when relevant.",
        "- Prefer concrete examples, code sketches, edge cases, and execution details over generic theory.",
        "- If the context does not support a full implementation, say what is missing and give the safest partial design.",
        "- Think through the problem before answering: identify the core constraint, then choose the most defensible implementation approach from the provided context.",
        "- When multiple designs are possible, briefly compare them and commit to one instead of staying generic.",
        "- Before answering, check that each major claim is supported by the retrieved notes or clearly marked as an inference.",
        "- Cite note paths inline.",
        "- Default to a natural technical answer, not a markdown note template.",
        "- Use headings or bullets only when they make the answer clearer; do not force a fixed markdown structure.",
    ]
    if reasoning_mode == "high":
        instructions.extend(
            (
                "- This request is in high reasoning mode: spend more effort choosing the strongest implementation path, not the fastest generic answer.",
                "- Expose important tradeoffs and then commit to one concrete recommendation.",
                "- Pull forward failure modes, invariants, and validation logic that would matter in real code.",
            )
        )
    if task_mode == "implementation":
        instructions.extend(
            (
                "- This request is in implementation mode: lead with a concrete build plan or code skeleton.",
                "- Name modules, functions, data structures, and execution order before broad explanation.",
                "- Prefer pseudocode or real code snippets when the context is strong enough.",
                "- If the user explicitly asks to generate code, do not stop at architecture alone: include concrete code or a file-by-file skeleton.",
                "- Call out assumptions, failure paths, cleanup rules, and validation steps that would matter during real implementation.",
                "- A light structure is welcome, but do not force the whole answer into a rigid markdown document shape.",
            )
        )
    response_contract = ""
    if task_mode == "implementation":
        response_contract = (
            "Preferred Coverage:\n"
            "- Cover implementation shape, concrete modules/functions, runtime flow, edge cases, and code skeleton when the context supports them.\n"
            "- You may use short sections or bullets if helpful, but exact heading names are optional.\n"
            "- If you start a code block for a file, finish that file before ending the answer.\n"
            "- Do not stop mid-function, mid-list, mid-file, or mid-sentence.\n"
            "- For small standalone programs, prefer one complete compile-ready version over several partial snippets.\n"
            "- If the user asked for code generation, include at least one concrete code block or explicit file-by-file skeleton.\n"
            "- Do not return only architecture, modules, and prose when the request explicitly asked for implementation code.\n"
            "- Make a concrete decision when multiple implementation paths exist; do not leave the design unresolved unless the notes are genuinely insufficient.\n"
            "- If a key design choice depends on an assumption, state that assumption explicitly near that choice.\n"
            "- Do not start with generic theory or motivational text."
        )
    sections = [
        f"Question:\n{retrieval.question}",
        "Task Mode:\n" + task_mode,
        "Reasoning Mode:\n" + reasoning_mode,
        "Instructions:\n" + "\n".join(instructions),
        response_contract,
        HIGH_REASONING_APPENDIX if reasoning_mode == "high" else "",
        format_context_section("Primary Notes", retrieval.primary_notes, retrieval.question),
        format_context_section("Related Notes", retrieval.related_notes, retrieval.question),
    ]
    return "\n\n".join(section for section in sections if section)


def format_context_section(
    title: str,
    notes: tuple[RetrievedNote, ...],
    question: str,
) -> str:
    if not notes:
        return f"{title}:\n- none"

    chunks = [f"{title}:"]
    for item in notes:
        chunks.append(
            "\n".join(
                [
                    f"- path: {item.note.path.as_posix()}",
                    f"  title: {item.note.title}",
                    f"  score: {item.score}",
                    f"  reason: {item.reason}",
                    "  excerpt:",
                    indent_block(excerpt(item.note.content, question)),
                ]
            )
        )
    return "\n".join(chunks)


def collect_citations(retrieval: RetrievalBundle) -> list[str]:
    seen: set[str] = set()
    citations: list[str] = []
    for item in (*retrieval.primary_notes, *retrieval.related_notes):
        path = item.note.path.as_posix()
        if path in seen:
            continue
        citations.append(path)
        seen.add(path)
    return citations

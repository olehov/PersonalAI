"""Generate a local-model note draft and scrub unsupported internal links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from application.knowledge.knowledge_service import KnowledgeService
from application.knowledge.retrieval_service import RetrievalService
from application.notes.link_sanitizer import (
    build_note_lookup,
    find_unsupported_obsidian_links,
    sanitize_generated_links,
)


SYSTEM_PROMPT = (
    "You write Obsidian markdown notes for a personal software engineering knowledge base. "
    "Return only the full markdown note content. "
    "Keep it factual, compact, and technically precise. "
    "Use internal links only when they refer to real related notes supplied in context. "
    "Never invent note titles, file paths, or graph links. "
    "Do not wrap the note in code fences."
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI for local note drafting."""
    parser = argparse.ArgumentParser(description="Generate a local-model Obsidian note draft.")
    parser.add_argument("--vault", type=Path, required=True, help="Path to the Obsidian vault root.")
    parser.add_argument("--model-path", required=True, help="Local Hugging Face or Unsloth adapter path.")
    parser.add_argument("--title", required=True, help="Canonical note title to generate.")
    parser.add_argument("--instruction", required=True, help="What the note should cover.")
    parser.add_argument(
        "--scope-dir",
        action="append",
        default=[],
        help="Restrict retrieval to one or more top-level directories.",
    )
    parser.add_argument(
        "--max-related-links",
        type=int,
        default=10,
        help="Maximum number of grounded related-note links to expose in the prompt.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=700,
        help="Maximum number of generated tokens.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def collect_allowed_links(
    retrieval_bundle,
    *,
    exclude_title: str,
    limit: int,
) -> tuple[str, ...]:
    """Derive a deduplicated set of real related note titles from retrieval context."""
    selected: list[str] = []
    seen: set[str] = {exclude_title.casefold()}
    for item in retrieval_bundle.primary_notes + retrieval_bundle.related_notes:
        title = item.note.title.strip()
        if not title:
            continue
        key = title.casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append(title)
        if len(selected) >= limit:
            break
    return tuple(selected)


def build_user_prompt(
    *,
    title: str,
    instruction: str,
    retrieval_bundle,
    allowed_links: tuple[str, ...],
) -> str:
    """Render the user prompt for local note generation."""
    citations = tuple(
        item.note.path.as_posix()
        for item in retrieval_bundle.primary_notes + retrieval_bundle.related_notes
    )
    lines = [
        f"Title: {title}",
        f"Instruction: {instruction}",
        "",
        "Rules:",
        "- Start the note with a level-1 markdown heading matching the title exactly.",
        "- Use plain Obsidian markdown.",
        "- Only emit internal links from the allowed list below.",
    ]
    if allowed_links:
        lines.append("- If no allowed link fits naturally, omit the link instead of inventing one.")
        lines.extend(
            [
                "",
                "Allowed internal links:",
                *[f"- [[{link_title}]]" for link_title in allowed_links],
            ]
        )
    else:
        lines.append("- Do not emit any internal links in this note.")

    lines.extend(
        [
            "",
            "Grounded context:",
            _render_retrieval_context(retrieval_bundle),
        ]
    )
    if citations:
        lines.extend(["", "Context note paths:", *[f"- {path}" for path in citations]])
    return "\n".join(lines)


def generate_note(
    *,
    model_path: str,
    system_prompt: str,
    user_prompt: str,
    max_new_tokens: int,
) -> str:
    """Generate note markdown from a local model or adapter."""
    from unsloth import FastLanguageModel
    import torch

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=4096,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    try:
        prompt_tensor = tokenizer.apply_chat_template(
            (
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ),
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(model.device)
        attention_mask = torch.ones_like(prompt_tensor)
        output = model.generate(
            input_ids=prompt_tensor,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
        generated = output[0][prompt_tensor.shape[1]:]
        return _strip_code_fences(tokenizer.decode(generated, skip_special_tokens=True)).strip() + "\n"
    finally:
        del model
        del tokenizer
        torch.cuda.empty_cache()


def _strip_code_fences(text: str) -> str:
    """Remove surrounding markdown code fences when the model wraps the note."""
    stripped = text.strip()
    fence_match = stripped.splitlines()
    if len(fence_match) >= 2 and fence_match[0].startswith("```") and fence_match[-1].strip() == "```":
        return "\n".join(fence_match[1:-1]).strip()
    return stripped


def _render_retrieval_context(retrieval_bundle) -> str:
    blocks: list[str] = []
    for label, notes in (
        ("Primary Notes", retrieval_bundle.primary_notes),
        ("Related Notes", retrieval_bundle.related_notes),
    ):
        if not notes:
            blocks.append(f"{label}:\n- none")
            continue
        lines = [f"{label}:"]
        for item in notes:
            excerpt = _note_excerpt(item.note.content)
            lines.extend(
                [
                    f"- title: {item.note.title}",
                    f"  path: {item.note.path.as_posix()}",
                    f"  reason: {item.reason}",
                    "  excerpt:",
                    *[f"    {line}" for line in excerpt.splitlines()],
                ]
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _note_excerpt(content: str, *, max_lines: int = 8) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines() if line.strip()]
    return "\n".join(lines[:max_lines]) if lines else "(empty)"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    knowledge = KnowledgeService(args.vault)
    knowledge.load()
    retrieval = RetrievalService(knowledge)
    retrieval_bundle = retrieval.build_context(
        f"{args.title}\n{args.instruction}",
        scope_dirs=tuple(args.scope_dir),
    )

    note_lookup = build_note_lookup(knowledge.list_notes())
    allowed_links = collect_allowed_links(
        retrieval_bundle,
        exclude_title=args.title,
        limit=args.max_related_links,
    )
    prompt = build_user_prompt(
        title=args.title,
        instruction=args.instruction,
        retrieval_bundle=retrieval_bundle,
        allowed_links=allowed_links,
    )
    raw_content = generate_note(
        model_path=args.model_path,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        max_new_tokens=args.max_new_tokens,
    )
    unsupported_before = find_unsupported_obsidian_links(raw_content, note_lookup)
    sanitized_content = sanitize_generated_links(raw_content, note_lookup)
    unsupported_after = find_unsupported_obsidian_links(sanitized_content, note_lookup)

    if args.format == "json":
        payload = {
            "title": args.title,
            "model_path": args.model_path,
            "allowed_links": list(allowed_links),
            "removed_links": list(unsupported_before),
            "remaining_unsupported_links": list(unsupported_after),
            "citations": [
                item.note.path.as_posix()
                for item in retrieval_bundle.primary_notes + retrieval_bundle.related_notes
            ],
            "content": sanitized_content,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(sanitized_content, end="")
    if unsupported_before:
        print("\nRemoved unsupported links:")
        for link in unsupported_before:
            print(f"- {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

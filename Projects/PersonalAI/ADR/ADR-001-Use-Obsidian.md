
# ADR-001 Use Obsidian

Status: Accepted

## Related Notes

- [[Project Index]]
- [[Vision]]
- [[Architecture]]
- [[Technology Stack]]
- [[PersonalAI MVP Overview]]

## Context

The assistant needs a human-readable knowledge base that can also serve as the long-term memory layer described in [[Vision]] and the document-centered architecture captured in [[Architecture]].

## Decision

Use Obsidian as the primary storage. This keeps the knowledge layer aligned with the current implementation shape documented in [[PersonalAI MVP Overview]] and with the tooling direction summarized in [[Technology Stack]].

## Consequences

Positive:
- Markdown notes remain easy to inspect, diff, and refactor over time.
- Git friendly storage keeps the vault compatible with local-first development workflows.
- Easy editing lets both a human and the assistant iterate on the same corpus without proprietary lock-in.

Negative:
- No built-in API, so the indexing and retrieval layers must be implemented in the application itself.

"""Knowledge, retrieval, and grounded answer domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


AnswerTaskMode = Literal["general", "implementation"]


@dataclass(frozen=True, slots=True)
class NoteLink:
    """Represents an internal Obsidian link found inside a note."""

    raw: str
    target: str
    alias: str | None = None


@dataclass(frozen=True, slots=True)
class NoteMetadata:
    """Structured metadata extracted from frontmatter."""

    values: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NoteDocument:
    """Structured representation of a markdown note."""

    path: Path
    title: str
    content: str
    metadata: NoteMetadata = field(default_factory=NoteMetadata)
    links: tuple[NoteLink, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RetrievedNote:
    """A note selected for a retrieval response with a simple relevance score."""

    note: NoteDocument
    score: int
    reason: str


@dataclass(frozen=True, slots=True)
class RetrievalBundle:
    """Structured context bundle for a future LLM or chat runtime."""

    question: str
    primary_notes: tuple[RetrievedNote, ...] = field(default_factory=tuple)
    related_notes: tuple[RetrievedNote, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PromptMessage:
    """Represents a single prompt message for an LLM adapter."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class AnswerBundle:
    """Structured answer payload prepared for a future LLM integration."""

    question: str
    retrieval: RetrievalBundle
    task_mode: AnswerTaskMode = "general"
    messages: tuple[PromptMessage, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    """Grounded answer returned by an LLM adapter."""

    model: str
    question: str
    answer_text: str
    citations: tuple[str, ...] = field(default_factory=tuple)
    prompt: AnswerBundle | None = None


@dataclass(frozen=True, slots=True)
class DirectoryAnalysisNodeStat:
    """Graph connectivity stats for a note inside a directory slice."""

    note: NoteDocument
    inbound_links: int = 0
    outbound_links: int = 0


@dataclass(frozen=True, slots=True)
class DirectoryCoverageSuggestion:
    """Suggested note or topic that would improve directory coverage."""

    title: str
    reason: str
    source: str


@dataclass(frozen=True, slots=True)
class DirectoryAnalysisReport:
    """Structured analysis of notes and graph coverage inside one directory."""

    directory: Path
    note_count: int
    notes: tuple[NoteDocument, ...] = field(default_factory=tuple)
    total_links: int = 0
    internal_link_count: int = 0
    cross_directory_link_count: int = 0
    unresolved_links: tuple[str, ...] = field(default_factory=tuple)
    isolated_notes: tuple[Path, ...] = field(default_factory=tuple)
    hub_notes: tuple[DirectoryAnalysisNodeStat, ...] = field(default_factory=tuple)
    suggestions: tuple[DirectoryCoverageSuggestion, ...] = field(default_factory=tuple)

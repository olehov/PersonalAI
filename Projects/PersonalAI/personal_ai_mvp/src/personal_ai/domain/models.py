"""Core domain models for notes and note relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal


AnswerTaskMode = Literal["general", "implementation"]
AgentStepKind = Literal["retrieval", "planning", "action_plan", "action_execution"]
AgentRunStatus = Literal["completed", "needs_execution_layer"]
AgentActionExecutionStatus = Literal["executed", "deferred", "failed"]
AgentTaskPlanStatus = Literal["completed", "next", "pending"]


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
class AgentRuntimeStep:
    """One step inside a lightweight agent-runtime artifact."""

    step_index: int
    kind: AgentStepKind
    title: str
    input_text: str
    output_text: str
    observation: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeAction:
    """A safe machine-readable next action proposed by the runtime."""

    action_type: str
    title: str
    target: str
    instruction: str
    rationale: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeActionExecution:
    """Execution outcome for one recommended runtime action."""

    action_type: str
    target: str
    status: AgentActionExecutionStatus
    output_text: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeTaskPlanEntry:
    """One structured task-plan item extracted from an agent planning run."""

    step_index: int
    title: str
    status: AgentTaskPlanStatus
    details: str
    source_section: str


@dataclass(frozen=True, slots=True)
class AgentRuntimeTaskPlan:
    """Structured task plan surfaced to the UI and future execution layers."""

    goal: str
    current_focus: str
    summary: str
    entries: tuple[AgentRuntimeTaskPlanEntry, ...] = field(default_factory=tuple)
    validation_checks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AgentRuntimeDiscussionTrace:
    """Trace of a multi-model planning discussion."""

    preset: str
    planner_draft: str
    critic_feedback: str | None = None
    synthesis_output: str | None = None
    fallback_used: str | None = None


@dataclass(frozen=True, slots=True)
class AgentRuntimeArtifact:
    """A reviewable artifact produced by the planning-oriented agent runtime."""

    model: str
    request_text: str
    normalized_goal: str
    task_mode: AnswerTaskMode
    status: AgentRunStatus
    executor_model: str | None = None
    critic_model: str | None = None
    synthesis_model: str | None = None
    discussion_preset: str | None = None
    discussion_trace: AgentRuntimeDiscussionTrace | None = None
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    steps: tuple[AgentRuntimeStep, ...] = field(default_factory=tuple)
    recommended_actions: tuple[AgentRuntimeAction, ...] = field(default_factory=tuple)
    action_executions: tuple[AgentRuntimeActionExecution, ...] = field(default_factory=tuple)
    task_plan: AgentRuntimeTaskPlan | None = None
    history_entry_id: int | None = None
    final_output: str = ""
    prompt: AnswerBundle | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class QueryHistoryEntry:
    """Persisted record of a grounded ask/query interaction."""

    entry_id: int
    created_at: datetime
    question: str
    answer_text: str
    model: str
    task_mode: AnswerTaskMode = "general"
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    latency_ms: int | None = None
    prompt_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class AgentRunHistoryEntry:
    """Persisted record of an agent-runtime execution artifact."""

    entry_id: int
    created_at: datetime
    request_text: str
    normalized_goal: str
    model: str
    task_mode: AnswerTaskMode
    status: AgentRunStatus
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    latency_ms: int | None = None
    artifact_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkRunHistoryEntry:
    """Persisted record of one benchmark-pack run artifact."""

    entry_id: int
    created_at: datetime
    pack_id: str
    task_id: str
    category: str
    workflow: str
    model: str
    status: str
    scope_dirs: tuple[str, ...] = field(default_factory=tuple)
    prompt_text: str = ""
    latency_ms: int | None = None
    result_payload: dict[str, object] | None = None


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


NoteChangeAction = Literal["create", "update", "refactor", "archive"]
MaintenanceFindingKind = Literal["empty_note", "sparse_note", "isolated_note", "duplicate_title"]


@dataclass(frozen=True, slots=True)
class NoteChangeProposal:
    """A proposed safe note mutation before any write occurs."""

    action: NoteChangeAction
    target_path: Path
    title: str
    reason: str
    proposed_content: str
    current_content: str | None = None
    archive_path: Path | None = None
    similar_notes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AppliedNoteChange:
    """Result of applying a safe note mutation."""

    action: NoteChangeAction
    target_path: Path
    backup_path: Path | None = None
    archive_path: Path | None = None
    applied_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class GeneratedNoteDraft:
    """LLM-generated markdown draft paired with a safe mutation proposal."""

    model: str
    title: str
    instruction: str
    content: str
    proposal: NoteChangeProposal
    citations: tuple[str, ...] = field(default_factory=tuple)
    companion_proposals: tuple[NoteChangeProposal, ...] = field(default_factory=tuple)
    prompt: AnswerBundle | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceFinding:
    """A maintenance issue detected in the knowledge base with an optional safe proposal."""

    kind: MaintenanceFindingKind
    note: NoteDocument
    summary: str
    details: tuple[str, ...] = field(default_factory=tuple)
    proposal: NoteChangeProposal | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenanceReport:
    """A collection of maintenance findings for the current vault state."""

    findings: tuple[KnowledgeMaintenanceFinding, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenancePlanEntry:
    """A single actionable maintenance step selected for batch review."""

    finding: KnowledgeMaintenanceFinding
    proposal: NoteChangeProposal
    merged_kinds: tuple[MaintenanceFindingKind, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class KnowledgeMaintenancePlan:
    """A compact batch of compatible maintenance proposals for review."""

    entries: tuple[KnowledgeMaintenancePlanEntry, ...] = field(default_factory=tuple)
    skipped_paths: tuple[str, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class MaintenanceDraftPlanEntry:
    """A generated maintenance draft attached to its planning context."""

    plan_entry: KnowledgeMaintenancePlanEntry
    draft: GeneratedNoteDraft


@dataclass(frozen=True, slots=True)
class MaintenanceDraftPlan:
    """A review-ready batch of generated maintenance drafts."""

    entries: tuple[MaintenanceDraftPlanEntry, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingExample:
    """A supervised example for future prompting or fine-tuning workflows."""

    example_id: str
    source: str
    quality_tier: str
    task: str
    source_note_path: Path
    title: str
    instruction: str
    input_markdown: str
    target_markdown: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TrainingCorpus:
    """A collection of supervised training examples derived from the vault."""

    examples: tuple[TrainingExample, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingCorpusManifest:
    """A compact summary of dataset composition and quality tiers."""

    total_examples: int
    by_source: dict[str, int] = field(default_factory=dict)
    by_quality_tier: dict[str, int] = field(default_factory=dict)
    by_task: dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingCorpusSplit:
    """A deterministic train/validation split with simple policy metadata."""

    train_examples: tuple[TrainingExample, ...] = field(default_factory=tuple)
    validation_examples: tuple[TrainingExample, ...] = field(default_factory=tuple)
    policy: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingFineTuneRecipe:
    """Recommended LoRA-style fine-tuning settings for a selected model family."""

    model_family: str
    dataset_format: str
    recommended_framework: str
    learning_rate: float
    num_epochs: int
    micro_batch_size: int
    gradient_accumulation_steps: int
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    max_sequence_length: int
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TrainingTrainerArtifact:
    """A trainer-specific configuration artifact generated from a fine-tune bundle."""

    trainer: str
    kind: str
    path: Path
    format: str


@dataclass(frozen=True, slots=True)
class TrainingFineTuneBundle:
    """A persisted fine-tuning bundle with dataset files and a recommended recipe."""

    bundle_dir: Path
    train_path: Path
    validation_path: Path
    manifest_path: Path
    recipe_path: Path
    runbook_path: Path
    source: str
    validation_ratio: float
    train_examples: int
    validation_examples: int
    recipe: TrainingFineTuneRecipe
    trainer_artifacts: tuple[TrainingTrainerArtifact, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingEvaluationExampleResult:
    """Evaluation outcome for a single training example."""

    example_id: str
    source_note_path: Path
    source: str
    quality_tier: str
    task: str
    model: str
    score: float
    exact_match: bool
    target_link_count: int
    output_link_count: int
    target_heading_count: int
    output_heading_count: int
    output_markdown: str


@dataclass(frozen=True, slots=True)
class TrainingEvaluationFailureSnapshot:
    """A compact view of a weak evaluation example for fast review."""

    example_id: str
    source_note_path: Path
    task: str
    score: float
    exact_match: bool
    output_markdown_preview: str
    error_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PromptPatchSuggestion:
    """A concrete prompt improvement suggestion derived from eval failures."""

    error_tag: str
    occurrences: int
    instruction: str
    rationale: str


@dataclass(frozen=True, slots=True)
class PromptPatchPlan:
    """A compact optimized prompt plan built from evaluation history."""

    base_system_prompt: str
    optimized_system_prompt: str
    suggestions: tuple[PromptPatchSuggestion, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingEvaluationComparison:
    """A side-by-side comparison between baseline and optimized eval runs."""

    model: str
    subset: str
    baseline_report: TrainingEvaluationReport
    optimized_report: TrainingEvaluationReport
    optimized_prompt_plan: PromptPatchPlan
    score_delta: float
    exact_match_rate_delta: float
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingOptimizerLeaderboardEntry:
    """Aggregate optimizer metrics for one model/subset pair."""

    model: str
    subset: str
    runs: int
    average_score_delta: float
    best_score_delta: float
    latest_score_delta: float
    average_exact_match_rate_delta: float
    latest_exact_match_rate_delta: float
    last_evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class TrainingOptimizerLeaderboard:
    """A compact leaderboard for prompt-optimization comparison runs."""

    entries: tuple[TrainingOptimizerLeaderboardEntry, ...] = field(default_factory=tuple)
    total_runs: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingOptimizerSweepReport:
    """A batch comparison summary across multiple models."""

    subset: str
    comparisons: tuple[TrainingEvaluationComparison, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingEvaluationReport:
    """Aggregate evaluation summary over a split subset."""

    model: str
    subset: str
    average_score: float
    exact_match_rate: float
    results: tuple[TrainingEvaluationExampleResult, ...] = field(default_factory=tuple)
    failure_snapshots: tuple[TrainingEvaluationFailureSnapshot, ...] = field(default_factory=tuple)
    prompt_patch_suggestions: tuple[PromptPatchSuggestion, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TrainingEvaluationLeaderboardEntry:
    """Aggregate leaderboard metrics for one model/subset pair."""

    model: str
    subset: str
    runs: int
    average_score: float
    best_score: float
    latest_score: float
    delta_vs_previous_score: float
    delta_vs_best_score: float
    average_exact_match_rate: float
    latest_exact_match_rate: float
    delta_vs_previous_exact_match_rate: float
    delta_vs_best_exact_match_rate: float
    last_evaluated_at: datetime
    latest_failure_snapshots: tuple[TrainingEvaluationFailureSnapshot, ...] = field(default_factory=tuple)
    prompt_patch_suggestions: tuple[PromptPatchSuggestion, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TrainingEvaluationLeaderboard:
    """A compact leaderboard built from saved evaluation history."""

    entries: tuple[TrainingEvaluationLeaderboardEntry, ...] = field(default_factory=tuple)
    total_runs: int = 0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

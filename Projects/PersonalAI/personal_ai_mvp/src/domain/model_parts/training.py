"""Training, evaluation, and optimization domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


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

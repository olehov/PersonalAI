# Planning Role Benchmark Report 2026-07-02

## Related Notes

- [[Benchmark Workflow Index]]
- [[Repo-Aware Benchmark Pack]]
- [[C Note Gap Benchmark Report 2026-07-02]]

## Benchmark Asset

- pack: `training_examples/benchmarks/planning_role_pack.json`
- raw results: `training_examples/benchmarks/results/planning_role_compare_2026-07-02.json`
- task: `personalai-next-step-planning`
- workflow: `agent`

## Goal

Compare local models on planner duty:

- reassess the current PersonalAI state
- reprioritize the next development round
- produce a narrow ordered plan
- stay honest about current implementation status

## High-Level Verdict

No tested model was excellent across all planning criteria.

The benchmark exposed four recurring planner failures:

- stale understanding of what is already implemented
- generic backlog expansion instead of reprioritization
- invented files, anchors, or validation steps
- weak separation between planning and implementation

## Best Current Planner Candidate

### qwen2.5-coder:7b

This was the strongest current baseline for planner duty, but only relatively.

Strengths:

- produced a clean ordered task-plan structure
- stayed in planning mode better than most others
- did not collapse completely or return an empty artifact
- kept the response narrow enough to be reviewable

Weaknesses:

- still spent too much effort planning how to inspect the roadmap instead of reprioritizing from it
- did not produce the sharpest concrete next milestone
- still needs a stronger planner-specific prompt contract

Recommended role:

- first-pass planner
- task decomposition
- plan skeleton generation before a stronger reviewer or executor model

## Secondary Candidates

### mistral:7b

Strengths:

- tried to reprioritize around benchmarks and evaluation work
- recognized that benchmark workflow quality matters right now

Weaknesses:

- bloated into an overlong 11-step plan
- invented note anchors and overreached on graph references
- less disciplined than `qwen2.5-coder:7b`

Recommended role:

- strategy brainstorming
- not the safest primary planner

### qwen2.5:7b

Strengths:

- returned a structured artifact
- recognized the need for concrete next actions

Weaknesses:

- hallucinated implementation details and file names
- blurred planning with feature invention
- weaker honesty than a planner should have

Recommended role:

- not primary planner
- maybe useful as a rough ideation model only

## Weak Fits For Planner Duty

### llama3:latest

- readable output, but stale understanding of current state
- suggested work that notes already describe as implemented
- weak reprioritization quality

### gemma:latest

- completed the run, but stayed too generic
- framed the answer more like a broad project note than a tight planner artifact

### gemma3:4b

- failed with an empty Ollama response on this planning task
- still the best note-drafting model from the previous benchmark, but not reliable here

### deepseek-r1:8b

- failed with an empty Ollama response on this planning task
- not currently reliable enough for planner duty in this pipeline

## Recommended Model Split Right Now

### Planner

- primary: `qwen2.5-coder:7b`
- backup: `mistral:7b`

### Drafting and knowledge-note generation

- primary: `gemma3:4b`
- backup: `llama3:latest`

### Why split the roles

- the best note-drafting model did not become the best planner
- the best planner candidate was worse at strict vault-style note generation
- this supports a multi-model pipeline rather than a one-model-for-everything setup

## Next Recommended Benchmark

The next useful comparison should test planner plus executor collaboration directly:

1. planner model produces a 3-step grounded first-slice plan
2. executor model produces only the first implementation slice
3. reviewer checks honesty, file targeting, and validation quality

That benchmark should tell us whether:

- `qwen2.5-coder:7b -> gemma3:4b`
- `qwen2.5-coder:7b -> llama3:latest`
- `mistral:7b -> gemma3:4b`

is the strongest current two-model pairing.

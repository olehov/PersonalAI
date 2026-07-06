# C Note Gap Benchmark Report 2026-07-02

## Related Notes

- [[Benchmark Workflow Index]]
- [[Repo-Aware Benchmark Pack]]
- [[Training Examples Knowledge Map]]

## Benchmark Asset

- pack: `training_examples/benchmarks/c_note_gap_pack.json`
- raw results: `training_examples/benchmarks/results/c_note_gap_compare_2026-07-02.json`
- task: `c-missing-note-draft`
- scope: `Languages/C`

## Goal

Compare local Ollama models on one grounded knowledge task:

- inspect the existing `Languages/C` note cluster
- identify exactly one missing topic
- draft one compact Obsidian note
- avoid invented links and formatting drift

## Quick Verdict

### Best fit right now

- `gemma3:4b`
  - strongest overall balance of speed, grounded topic choice, valid Obsidian links, and usable note structure
  - best current candidate for note-gap detection and first-pass knowledge drafting

### Useful with prompt cleanup

- `llama3:latest`
  - fast and generally on-topic
  - still drifts in formatting, but the underlying note idea was usable
- `mistral:7b`
  - stayed close to the C cluster and picked a sensible topic
  - wrapped the draft in code fences, so it is better as a rewrite candidate than a direct note generator
- `qwen2.5-coder:7b`
  - produced a plausible topic choice
  - ignored the requested output contract and drifted toward a more implementation-style answer

### Weak for this workflow

- `gemma:latest`
  - proposed a broad systems topic and invented unsupported links
  - weaker graph discipline than `gemma3:4b`
- `qwen2.5:7b`
  - largely missed the task shape and returned the wrong response format
- `deepseek-r1:8b`
  - extremely slow on this benchmark and collapsed into an unusably small answer

## Per-Model Snapshot

### gemma3:4b

- latency: about `26.6s`
- chosen topic: `Binary Data Formats`
- result quality:
  - clean structure
  - no invented links detected
  - valid `## Related Notes` section
  - practical note content

### gemma:latest

- latency: about `68.8s`
- chosen topic: `Concurrency and Synchronization in C`
- result quality:
  - topic was too broad for the current C cluster
  - invented unsupported links
  - weaker fit for vault-style note drafting

### qwen2.5:7b

- latency: about `66.8s`
- chosen topic: unclear
- result quality:
  - missed the requested three-section contract
  - drifted into generic implementation framing
  - not usable as a direct note draft

### qwen2.5-coder:7b

- latency: about `29.6s`
- chosen topic: `Advanced Memory Management in C`
- result quality:
  - sensible missing topic candidate
  - ignored the note-only response contract
  - better fit for implementation planning than vault drafting

### mistral:7b

- latency: about `44.3s`
- chosen topic: `Serialization and Deserialization in C`
- result quality:
  - grounded and relevant
  - wrapped the note in fenced markdown
  - salvageable with stronger formatting constraints

### llama3:latest

- latency: about `13.5s`
- chosen topic: `Data Profiling and Validation in C`
- result quality:
  - fast and reasonably relevant
  - formatting still drifted from the strict requested structure
  - usable as a brainstorming model, not yet the safest direct drafter

### deepseek-r1:8b

- latency: about `812.6s`
- chosen topic: `Concurrency in C`
- result quality:
  - far too slow for this workflow
  - answer collapsed and was not usable as a real draft
  - poor cost-to-quality ratio for note drafting

## Process Recommendation

### Knowledge drafting

- primary: `gemma3:4b`
- backup: `mistral:7b` or `llama3:latest`

### Implementation planning

- primary candidates to test next: `qwen2.5-coder:7b`, `llama3:latest`, `deepseek-r1:8b`
- reason:
  - these models are more likely to show value on repo and coding workflows than on strict vault-style note drafting

### Models to avoid for direct note writes

- `gemma:latest`
- `qwen2.5:7b`
- `deepseek-r1:8b`

## Next Benchmark Suggestion

To map models to roles more precisely, run the next two tasks separately:

- one `implementation` benchmark on a small repo slice
- one `agent` benchmark on first-slice planning with file targeting and validation

That should give a cleaner split between:

- note drafting models
- implementation-planning models
- agent/planner models

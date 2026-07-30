# Planner Executor Pair Benchmark Report 2026-07-02

## Related Notes

- [[Benchmark Workflow Index]]
- [[Planning Role Benchmark Report 2026-07-02]]
- [[Python Task CLI Benchmark Project]]

## Benchmark Asset

- raw results: `training_examples/benchmarks/results/planner_executor_pair_compare_2026-07-02.json`
- rerun after planner-grounding fix: `training_examples/benchmarks/results/planner_executor_pair_compare_2026-07-02_rerun.json`
- pack: `training_examples/benchmarks/simple_project_pack.json`
- task: `python-task-cli-agent-first-slice`

## Tested Pairs

- `qwen2.5-coder:7b -> qwen2.5-coder:7b`
- `qwen2.5-coder:7b -> gemma3:4b`
- `qwen2.5-coder:7b -> llama3:latest`
- `mistral:7b -> gemma3:4b`

## Main Finding

Planner quality dominated the final result much more than executor choice.

Across all tested pairs:

- repo inspection correctly surfaced the real file tree
- the runtime saw `src/task_cli/cli.py`, `src/task_cli/store.py`, `tests/test_cli.py`, and `tests/test_store.py`
- but the planner still hallucinated replacement files such as `tasks.py`, `task_manager.py`, and `task_storage.py`

That means the current bottleneck is not primarily executor drafting quality. It is planner grounding and planner adherence to the inspected repository structure.

## Pair Verdicts

### Best current baseline

- `qwen2.5-coder:7b -> qwen2.5-coder:7b`

Why:

- fastest strong baseline among the tested pairs
- produced a readable first-slice artifact
- still wrong on file targeting, but more coherent than the others

Weakness:

- invented `task_manager.py`
- treated missing persistence as a greenfield design instead of extending `store.py`

### Best split-pair candidate so far

- `qwen2.5-coder:7b -> gemma3:4b`

Why:

- the cleanest current split experiment
- executor stayed stable and the run completed cleanly
- worth keeping as the main split-pair candidate for future retests

Weakness:

- planner hallucination still poisoned the handoff
- the pair did not materially fix wrong module targeting

### Usable but weaker split

- `qwen2.5-coder:7b -> llama3:latest`

Why:

- still coherent enough to inspect

Weakness:

- planner drift remained
- handoff still referenced likely-nonexistent `tasks.py`
- no clear gain over the `gemma3:4b` executor

### Weakest tested pair

- `mistral:7b -> gemma3:4b`

Why:

- the planner mixed in unrelated style rules and noisy context
- project understanding drifted the most
- file targeting was still wrong despite correct repo inspection

## Practical Recommendation

Right now the strongest pair to keep experimenting with is:

- `qwen2.5-coder:7b -> gemma3:4b`

But this is only a provisional winner.

It is not yet a trustworthy implementation pair because:

- the planner still ignores the inspected real file tree
- first-slice planning is still too willing to invent new modules

## What This Means For The Roadmap

The next high-value improvement is not “find a better executor”.

The next high-value improvement is:

- tighten planner prompts so file targeting must anchor to inspected repo files
- force the planner to justify any new file creation against the existing tree
- penalize plans that ignore already-inspected target files

## Rerun After Planner-Grounding Tightening

After injecting repo summary, file tree, suggested files, and target file snippets directly into the planning prompt, the pair benchmark improved materially.

Main change:

- the planner stopped hallucinating `tasks.py`, `task_manager.py`, and `task_storage.py`
- the better runs started anchoring to the real repository structure around `task_cli/cli.py`, `task_cli/store.py`, and the existing tests

### Updated verdict

- `qwen2.5-coder:7b -> gemma3:4b` is still the best current split pair
- `qwen2.5-coder:7b -> qwen2.5-coder:7b` is now the best single-family baseline

### Why the rerun is better

- planner output now names real files from the repo tree
- first-slice planning is much closer to extending existing code instead of redesigning the project
- executor choice still matters, but planner grounding now matters less because the planner is no longer poisoning the handoff as badly

### Remaining weakness

The planner is now much better at avoiding fake file names, but it is still inconsistent about naming both key files in the same first slice:

- some runs anchored mainly on `cli.py`
- others anchored mainly on `store.py`

That means the next refinement should be about first-slice completeness and cross-file coordination, not basic file-path honesty.

## Revised Recommendation

Right now the strongest current pair to keep is:

- `qwen2.5-coder:7b -> gemma3:4b`

And the strongest fallback is:

- `qwen2.5-coder:7b -> qwen2.5-coder:7b`

## New Next Step

The next improvement should not be another broad model sweep.

It should be a planner-contract refinement that says:

- when the first slice needs both a storage change and a CLI wiring change, mention both files explicitly
- justify why one file is the primary edit point and the other is the integration point
- treat omission of an obvious paired file as a soft quality failure

## Recommended Next Benchmark

Run one more pair benchmark after planner-prompt tightening with these rules:

- planner must name only files found by `inspect_file_tree` unless it explicitly explains why a new file is required
- planner must prefer extending existing files before proposing new modules
- reviewer should mark invented file paths as a hard failure

After that, retest:

- `qwen2.5-coder:7b -> gemma3:4b`
- `qwen2.5-coder:7b -> llama3:latest`
- `qwen2.5-coder:7b -> qwen2.5-coder:7b`

If the planner still hallucinates file names after that change, the next priority should be planner prompt redesign or planner post-validation, not more executor swapping.

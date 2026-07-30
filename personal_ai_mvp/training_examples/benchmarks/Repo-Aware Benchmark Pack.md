# Repo-Aware Benchmark Pack

## Related Notes

- [[Benchmark Workflow Index]]
- [[Training Examples Knowledge Map]]
- [[PersonalAI MVP Overview]]
- [[Python Task CLI Benchmark Project]]
- [[Mistral Curated Full Adapter Model Card]]
- [[Mistral Ukrainian Full Adapter Model Card]]

This directory holds repeatable benchmark tasks for PersonalAI's repo-aware coding workflows.

Current pack:

- `repo_aware_pack.json`
- `multi_turn_coding_pack.json`
- `simple_project_pack.json`
- `c_note_gap_pack.json`

Recent result artifacts:

- [[C Note Gap Benchmark Report 2026-07-02]]

The pack is designed to evaluate:

- grounded coding answers
- repository analysis
- implementation scoping
- multi-turn continuation
- first-slice code drafting
- execution honesty

Suggested usage:

1. List the pack through the CLI:
   `cmd /c "set PYTHONPATH=src&& python -m cli --vault H:\KnowledgeBase\KnowledgeBase benchmark-pack"`
2. Filter to one task:
   `cmd /c "set PYTHONPATH=src&& python -m cli --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-pack --task-id execution-honesty-minishell-build"`
3. Filter to just continuation regressions:
   `cmd /c "set PYTHONPATH=src&& python -m cli --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-pack --pack-file training_examples\benchmarks\multi_turn_coding_pack.json --category multi_turn_continuation"`
4. Compare only continuation tasks across models:
   `cmd /c "set PYTHONPATH=src&& python -m cli --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-compare --pack-file training_examples\benchmarks\multi_turn_coding_pack.json --category multi_turn_continuation --model gpt-oss:20b --model qwen2.5-coder:7b"`
5. Save the resulting agent artifact or answer output for model comparison.

Multi-turn tasks:

- `multi-turn-bsq-c-continuation`
- `multi-turn-minishell-slice-continuation`

These tasks are meant to catch a common failure mode: the model gives a decent first answer, then loses continuity on the next prompt and starts over. The benchmark runner now executes these turns sequentially and carries forward prior user and assistant messages as conversation history.

Review rules:

- prefer exact file and repo references over generic advice
- treat false execution claims as hard failures
- reward narrow first slices over all-at-once project claims
- penalize follow-up turns that restart instead of continuing

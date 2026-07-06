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
- `simple_project_pack.json`
- `c_note_gap_pack.json`

Recent result artifacts:

- [[C Note Gap Benchmark Report 2026-07-02]]

The pack is designed to evaluate:

- grounded coding answers
- repository analysis
- implementation scoping
- first-slice code drafting
- execution honesty

Suggested usage:

1. List the pack through the CLI:
   `python -m personal_ai --vault "H:\KnowledgeBase\KnowledgeBase" benchmark-pack`
2. Filter to one task:
   `python -m personal_ai --vault "H:\KnowledgeBase\KnowledgeBase" --format json benchmark-pack --task-id execution-honesty-minishell-build`
3. Run the selected task manually through the matching workflow in the UI or CLI.
4. Save the resulting agent artifact or answer output for model comparison.

Review rules:

- prefer exact file and repo references over generic advice
- treat false execution claims as hard failures
- reward narrow first slices over all-at-once project claims

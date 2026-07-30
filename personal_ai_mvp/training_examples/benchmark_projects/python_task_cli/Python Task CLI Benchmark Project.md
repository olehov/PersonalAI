# Python Task CLI Benchmark Project

## Related Notes

- [[Benchmark Projects Index]]
- [[Benchmark Workflow Index]]
- [[PersonalAI MVP Overview]]
- [[Repo-Aware Benchmark Pack]]

Tiny reference project for PersonalAI benchmark runs.

This project is intentionally small so it can act as a repeatable implementation target inside [[Repo-Aware Benchmark Pack]] and the broader evaluation loop collected in [[Benchmark Workflow Index]]. In practice, it gives [[PersonalAI MVP Overview]] a narrow coding task where planning, file targeting, and truthful execution can be measured without hiding behind a large repository.

Current state:

- tasks are stored in a JSON file
- the CLI can add tasks
- the CLI can list tasks
- the CLI does not yet support marking a task as done

Desired next feature:

- add a `done` command
- mark one task complete by id
- persist the updated state
- keep the first implementation slice narrow so benchmark runs stay comparable across models

Suggested files to inspect:

- `src/task_cli/store.py`
- `src/task_cli/cli.py`
- `tests/test_store.py`
- `tests/test_cli.py`

That file layout also makes the project a good bridge between simple benchmark cases and more agentic flows such as the ones indexed in [[Agent Runtime Cases Index]].

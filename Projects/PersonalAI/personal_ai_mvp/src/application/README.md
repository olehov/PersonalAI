# Application Layout

This package now uses feature-oriented subpackages as the canonical implementation
layout.

## Canonical packages

- `agent_runtime/` - planner, executor, approver, discussion, action execution
- `benchmark/` - benchmark packs and benchmark execution services
- `chat/` - request preprocessing, routing, chat history, generation helpers
- `knowledge/` - retrieval, vault-facing knowledge services, directory analysis
- `notes/` - draft generation, mutation, maintenance, note policy helpers
- `shared/` - shared prompt-style and serialization helpers
- `training/` - corpus generation, eval flows, fine-tune preparation

## Remaining compatibility wrappers

There are no remaining flat compatibility wrapper modules under `application/`.
Feature code now lives only in the canonical subpackages.

## Migration rule

When editing or adding functionality:

1. Change the canonical subpackage module first.
2. Do not reintroduce flat wrapper files.
3. Do not add new business logic outside the canonical feature packages.

## Planned cleanup

After the migration is fully stable:

1. Update all imports to canonical package paths.
2. Keep `application/__init__.py` as the curated public facade only.
3. Continue reducing facade-style re-exports when they stop providing value.

## Current root layout

The project no longer uses `src/personal_ai/...`.

Current top-level source layout:

- `src/application/`
- `src/cli_app/`
- `src/domain/`
- `src/infrastructure/`
- `src/web_app/`
- `src/cli.py`
- `src/web_ui.py`

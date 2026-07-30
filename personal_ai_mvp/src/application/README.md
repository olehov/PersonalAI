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

## Runtime configuration notes

The package layout migration also changed how runtime configuration should be
reasoned about:

- do not assume the project is always launched from one checkout root
- prefer `PERSONAL_AI_HOME` or `PERSONAL_AI_ENV_FILE` for project-relative assets
- treat checkout-relative fallback logic as compatibility behavior, not as the primary contract

Current configuration behavior:

- `infrastructure.config.env_loader.default_env_file_path()` resolves `.env` from:
  `PERSONAL_AI_ENV_FILE` -> `PERSONAL_AI_HOME` / `PERSONAL_AI_PROJECT_ROOT` -> cwd parent search -> checkout fallback
- `infrastructure.config.settings.project_root_path()` resolves project-relative assets from:
  `PERSONAL_AI_HOME` / `PERSONAL_AI_PROJECT_ROOT` -> loaded `.env` parent -> checkout fallback

This keeps `training_examples/`, `frontend/dist/`, eval history, and fine-tune
bundles portable when the package is launched outside the repository root.

## Web app preprocessing rule

`web_app.app.PersonalAIWebApp.auto_run()` is expected to preprocess a prompt
exactly once, then route and execute using the already prepared text.

- do not add second-pass preprocessing inside downstream auto-run branches
- if a workflow method needs to accept already prepared text, thread a prepared
  payload explicitly instead of calling the preprocessor again

This matters because translation mode can otherwise pay double LLM cost and
drift the text on a second translation pass.

## Web API error policy

The JSON API uses a safe error boundary by default:

- validation errors may return direct user-facing messages
- unhandled server errors return a stable `"Internal server error."`
- detailed exception text is available only in logs unless
  `PERSONAL_AI_DEBUG_API_ERRORS=true`

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

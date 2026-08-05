# Development

## Environment Setup

Copy the local environment template:

```powershell
Copy-Item .env.example .env
```

## Runtime Commands

```powershell
npm run runtime:start
npm run runtime:status
npm run runtime:restart
npm run runtime:stop
```

Frontend-only:

```powershell
npm run frontend:dev
npm run frontend:build
```

## Backend Entry

```powershell
cmd /c "set PYTHONPATH=src&& python -m web_app.cli --vault H:\KnowledgeBase\KnowledgeBase"
```

## Test Commands

Full suite:

```powershell
cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests"
```

Focused benchmark suite:

```powershell
cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_cli_benchmark"
```

## Packaging

- Python packaging is managed through `pyproject.toml`
- frontend runtime commands are exposed through root `package.json`

## Contribution Expectations

When changing behavior:

- add or update a regression test when practical
- keep runtime/config values in `.env`-driven settings
- avoid hardcoded machine-specific paths
- preserve local-first behavior unless a hosted integration is explicitly optional

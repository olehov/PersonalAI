# PersonalAI MVP Overview

## Related Notes

- [[PersonalAI MVP Knowledge Map]]
- [[Repo-Aware Benchmark Pack]]
- [[Python Task CLI Benchmark Project]]
- [[Mistral Curated Full Adapter Model Card]]
- [[Mistral Ukrainian Full Adapter Model Card]]

PersonalAI is a local-first AI developer assistant that uses an Obsidian vault as its primary knowledge source.

## Architectural Reasoning

This MVP implements only the first phase of the system:

- read an Obsidian vault
- build structured document objects
- provide an in-memory knowledge index

The code is split into three layers to keep the core small and extensible:

- `domain`: pure data models that describe notes, metadata, and relationships
- `application`: use-case level logic for querying and navigating indexed knowledge
- `infrastructure`: file-system and Obsidian-specific parsing concerns

Supporting runtime packages sit alongside those layers:

- `cli_app`: CLI parsing, dispatch, and rendering
- `web_app`: HTTP API, app bootstrap, and web UI backend wiring

This separation keeps the note model independent from storage details and prepares the project for future additions such as embeddings, Qdrant, Ollama, and autonomous note updates.

## Package Layout

```text
personal_ai_mvp/
  pyproject.toml
  PersonalAI MVP Overview.md
  src/
    application/
    cli_app/
    domain/
    infrastructure/
    web_app/
  tests/
  training_examples/
```

## Current Scope

Implemented:

- recursive vault scanning
- markdown discovery
- UTF-8 file loading
- frontmatter extraction
- Obsidian link extraction
- in-memory note index
- related-note lookup
- grounded retrieval bundles
- local Ollama-backed ask flow
- safe note draft and write pipeline
- maintenance analysis and maintenance drafts
- agent runtime planning and execution handoff artifacts
- benchmark and training/evaluation workflows

Still future-facing:

- external vector stores such as Qdrant
- production-grade fine-tuned model serving
- fully autonomous multi-step code execution

## Running Tests

```bash
cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests"
```

## Environment File

Runtime configuration can now live in a local `.env` file at the project root.

Start by copying:

```bash
copy .env.example .env
```

Supported variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_HOST`
- `OLLAMA_MODELS`
- `OLLAMA_TIMEOUT_SECONDS`
- `PERSONAL_AI_DEFAULT_MODEL`
- `PERSONAL_AI_RECURSIVE_REFINEMENT`
- `PERSONAL_AI_CHAT_RECURSIVE_REFINEMENT`
- `PERSONAL_AI_AGENT_RECURSIVE_REFINEMENT`

Precedence:

- explicit CLI flags
- existing shell environment variables
- values loaded from `.env`
- code defaults

## React Frontend

The project now also includes a JS frontend scaffold in `frontend/` built with React and Vite.

Backend:

```bash
cmd /c "set PYTHONPATH=src&& python -m web_app.cli --vault H:\KnowledgeBase\KnowledgeBase"
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` requests to the local Python backend at `http://127.0.0.1:8765`.

If you want Ollama models to stay on a non-default drive such as `E:\OllamaModels`, keep that path in `.env` and start the local stack through the runtime manager:

```bash
powershell -ExecutionPolicy Bypass -File .\manage_runtime.ps1 -Action start
```

Useful variants:

```bash
powershell -ExecutionPolicy Bypass -File .\manage_runtime.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\manage_runtime.ps1 -Action restart
powershell -ExecutionPolicy Bypass -File .\manage_runtime.ps1 -Action stop
powershell -ExecutionPolicy Bypass -File .\manage_runtime.ps1 -Action start -Components ollama,backend
```

The same controls are also exposed through root `npm` scripts:

```bash
npm run runtime:start
npm run runtime:status
npm run runtime:restart
npm run runtime:stop
npm run runtime:start:ollama
npm run runtime:start:backend
npm run runtime:start:frontend
```

The runtime manager loads `.env`, applies `OLLAMA_HOST` and `OLLAMA_MODELS`, and can manage:

- `ollama`
- `backend`
- `frontend`

The older `start_ollama.ps1` helper still works as a compatibility wrapper for `ollama` only.

Current backend/runtime entrypoints:

- CLI script: `personal-ai` -> `cli_app.entry:main`
- Web script: `personal-ai-web` -> `web_app.cli:main`
- Direct module entry: `python -m cli_app.entry`
- Direct module entry: `python -m web_app.cli`

Current API routes:

- `POST /api/ask`
- `GET /api/ask-history?limit=10`
- `GET /api/agent-history?limit=10`
- `GET /api/history-overview`
- `GET /api/history?limit=10`
- `GET /api/models`
- `POST /api/analyze-dir`
- `POST /api/auto-route`
- `POST /api/auto-run`
- `POST /api/implementation-scope`
- `POST /api/agent-runtime`
- `POST /api/agent-task-plan`
- `POST /api/draft-note`
- `POST /api/reload`

## Local History Retention

The local SQLite history database is treated as an audit log, not as a second knowledge store.

- ask history keeps the newest `200` entries
- agent runtime history keeps the newest `120` entries
- benchmark history keeps the newest `200` entries
- stored prompt and artifact payloads are compacted before persistence

## CLI

The MVP includes a small command-line interface for exploring a vault locally.

Examples:

```bash
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase list"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase search architecture"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase related Projects/PersonalAI/Architecture.md"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase scan"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json retrieve \"heap complexity\" --scope-dir Algorithms"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json show Projects/PersonalAI/Architecture.md"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json retrieve \"how does PersonalAI architecture work\""
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json answer \"how does PersonalAI architecture work\""
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase ask \"how does PersonalAI architecture work\" --model llama3:latest"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json propose-note --title Heap --content-file draft.md --target-dir Algorithms"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json write-note --title Heap --content-file draft.md --target-dir Algorithms --approve"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json draft-note --title Heap --instruction \"Create a concise note about heap basics and operations.\" --target-dir Algorithms --scope-dir Algorithms --model llama3:latest"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json draft-write-note --title Heap --instruction \"Update the note with complexity details.\" --target-dir Algorithms --scope-dir Algorithms --model llama3:latest --approve"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json maintenance"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json maintenance-draft --note Projects/PersonalAI/Technology Stack.md --kind sparse_note --model llama3:latest"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json maintenance-draft-write --note Projects/PersonalAI/Technology Stack.md --kind sparse_note --model llama3:latest --approve"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json training-bundle --source curated --model-family mistral"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-pack"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-run --task-id execution-honesty-minishell-build --model deepseek-r1:8b"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-history --limit 10"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-compare --task-id repo-analysis-minishell-layout --model gemma:latest --model deepseek-r1:8b"
```

Use `--format json` when the CLI output is intended for another tool or agent runtime.

## Repo-Aware Benchmark Pack

The MVP now includes a repo-aware benchmark pack in `training_examples/benchmarks/repo_aware_pack.json`.

Use it to review repeatable tasks for:

- grounded coding answers
- repository analysis
- implementation scoping
- first-slice code drafting
- execution honesty

Examples:

```bash
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase benchmark-pack"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-pack --task-id execution-honesty-minishell-build"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-run --task-id repo-analysis-minishell-layout --model gemma:latest"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-history --limit 10"
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json benchmark-compare --task-id repo-analysis-minishell-layout --model gemma:latest --model deepseek-r1:8b"
```

## Retrieval Bundle

The `retrieve` command prepares the next architectural step toward chat:

- ranks notes using simple lexical matching
- blends lexical ranking with local vector similarity
- expands the result set with linked notes
- returns a structured context bundle for a future LLM integration

This keeps Phase 1 dependency-light while creating a clean seam for later semantic retrieval.

## Local Embeddings

The current vector retrieval layer is local and in-memory:

- deterministic hashed embeddings with no extra packages
- in-memory vector index rebuilt from vault notes
- hybrid retrieval that combines lexical score, path heuristics, and semantic similarity

This is an intermediate step before switching to dedicated embedding models and Qdrant.

## Retrieval Scopes

Commands that depend on retrieval can be narrowed with `--scope-dir`.

- supported on `retrieve`, `answer`, `ask`, `draft-note`, and `draft-write-note`
- useful when you already know the target knowledge bucket such as `Algorithms` or `Linux`
- for generated note drafts, `--target-dir` also helps derive a sensible default scope

## Answer Payload

The `answer` command does not call an LLM yet. Instead it prepares:

- a grounded system prompt
- a user prompt with note excerpts
- citations derived from retrieved notes
- a stable JSON payload for a future Ollama or API adapter

## Ollama Integration

The `ask` command now connects the grounded answer payload to a local Ollama model.

- default model: controlled by `PERSONAL_AI_DEFAULT_MODEL`
- transport: controlled by `OLLAMA_BASE_URL`
- dependency model: Python standard library only

## Safe Note Write Pipeline

The note mutation pipeline follows the vault rules for `CREATE`, `UPDATE`, `REFACTOR`, and `ARCHIVE`.

- `propose-note` builds a write proposal without touching the vault
- `write-note` requires `--approve` before any change is applied
- updates and refactors create backups in `.history/<timestamp>/...`
- archives preserve history first and then move notes into `Archive/<date>/...`
- restricted paths such as `.obsidian`, `.trash`, `.history`, and the MVP code folder are blocked

## Generated Drafts

The draft pipeline connects Ollama to the safe note workflow.

- `draft-note` generates markdown from grounded vault context and returns a proposal
- `draft-write-note` generates the same draft and applies it only with `--approve`
- generated drafts still pass through policy checks, warnings, backups, and archive rules

## Continuous Knowledge Maintenance

The `maintenance` command inspects the vault for low-signal notes that may need cleanup.

- detects empty notes and can suggest `archive` for Inbox-style stubs
- detects sparse notes that likely need expansion or consolidation
- detects isolated notes with no links and no backlinks
- detects duplicate normalized titles for manual merge review
- returns machine-readable proposals without applying changes automatically

## Maintenance Drafts

The maintenance workflow can now turn actionable findings into grounded refactor drafts.

- `maintenance-draft` selects a finding for a note and generates a refactor draft through Ollama
- `maintenance-draft-write` generates the same draft and applies it only with `--approve`
- only actionable `refactor` findings are drafted automatically
- duplicate-title and archive-only findings still require manual review

## Fine-Tuning Bundles

The project can now export train-ready LoRA bundles from the supervised corpus.

- `training-bundle` writes `train.jsonl`, `validation.jsonl`, `manifest.json`, `recipe.json`, and `RUNBOOK.md`
- it also writes starter trainer configs for `Unsloth` and `LLaMA-Factory`
- it also writes starter PowerShell launch scripts for both trainers
- bundles use the same chat-style dataset shape as the training/eval loop
- the recipe is intentionally framework-light: it gives stable starting hyperparameters without locking the project to one trainer yet
- current intent is to move from prompt-only optimization toward real adapter training while keeping the vault-specific evaluation loop in place

## Ukrainian Supervised Corpus

The training pipeline now supports a dedicated Ukrainian dataset source alongside the existing curated and synthetic note corpora.

- dataset path: `training_examples/ukrainian/`
- source flag: `--source ukrainian`
- intended use: grammar cleanup, punctuation normalization, technical Ukrainian phrasing, and style correction

Example:

```bash
cmd /c "set PYTHONPATH=src&& python -m cli_app.entry --vault H:\KnowledgeBase\KnowledgeBase --format json training-bundle --source ukrainian --model-family mistral"
```

For local before/after evaluation of a base model versus a trained adapter, use:

```bash
python compare_local_models.py ^
  --vault "H:\KnowledgeBase\KnowledgeBase" ^
  --source ukrainian ^
  --base-model "unsloth/mistral-7b-instruct-v0.3-bnb-4bit" ^
  --adapter-model "H:\KnowledgeBase\KnowledgeBase\Projects\PersonalAI\personal_ai_mvp\training_examples\fine_tune\mistral_ukrainian\outputs-full-ukrainian" ^
  --base-label mistral-base-local ^
  --adapter-label mistral-ukrainian-lora ^
  --output "training_examples\ukrainian_eval_compare.json"
```

The script writes:

- a JSON payload to `--output`
- a readable markdown report next to it by default, or to `--report-output` if provided

Both files use a UTF-8 BOM (`utf-8-sig`) so Windows editors handle Ukrainian text more reliably.

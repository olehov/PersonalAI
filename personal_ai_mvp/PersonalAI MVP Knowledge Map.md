# PersonalAI MVP Knowledge Map

## Purpose

This note is the top-level map for the `personal_ai_mvp` project subtree.

It links the main product overview, runtime surfaces, benchmark workflows, benchmark projects, and fine-tuning artifacts so the graph has one clear project entrypoint.

## Core Notes

- [[Project Index]]
- [[PersonalAI MVP Overview]]
- [[Training Examples Knowledge Map]]
- [[Repo-Aware Benchmark Pack]]
- [[Python Task CLI Benchmark Project]]
- [[Technology Stack]]
- [[Roadmap]]
- [[Agent Smith Analysis]]

## Runtime Surfaces

- CLI entrypoint: `cli_app.entry`
- Web backend entrypoint: `web_app.cli`
- Runtime manager: `manage_runtime.ps1`
- Frontend shell: `frontend/`

## Code Structure

The live Python package now maps cleanly by responsibility:

- `src/domain`
  Pure models and shared types.
- `src/application/knowledge`
  Vault indexing, retrieval, grounded answers, and directory analysis.
- `src/application/chat`
  Request preprocessing, routing, follow-up handling, and chat orchestration.
- `src/application/notes`
  Draft generation, write policy, mutation safety, and maintenance workflows.
- `src/application/agent_runtime`
  Planning, discussion, execution scaffolding, repo inspection, and tool orchestration.
- `src/application/benchmark`
  Benchmark pack loading and benchmark execution.
- `src/application/training`
  Corpus export, evaluation, comparison history, and fine-tune bundle generation.
- `src/cli_app`
  CLI parsers, handlers, dispatch, and terminal rendering.
- `src/web_app`
  HTTP routes, backend bootstrap, API helpers, and web UI integration.
- `src/infrastructure/config`
  `.env` loading and runtime settings.
- `src/infrastructure/llm`
  Ollama, OpenAI, routing-model, and model-client adapters.
- `src/infrastructure/history`
  SQLite-backed ask, agent, and benchmark history persistence.
- `src/infrastructure/vault`
  Vault reader and frontmatter parsing.

## Training Areas

- [[Benchmark Workflow Index]]
- [[Benchmark Projects Index]]
- [[Fine-Tuning Artifact Index]]
- [[Agent Runtime Cases Index]]

## Model Artifacts

- [[Mistral Curated Full Adapter Model Card]]
- [[Mistral Curated Full Adapter V2 Model Card]]
- [[Mistral Curated Smoke Adapter Model Card]]
- [[Mistral Ukrainian Full Adapter Model Card]]
- [[Mistral Ukrainian Smoke Adapter Model Card]]

## Navigation Hints

- Start with [[PersonalAI MVP Overview]] for product surface and runtime behavior.
- Use this note when you need the high-level map of code areas after the refactor that removed legacy wrapper modules.
- Use [[Repo-Aware Benchmark Pack]] when comparing model behavior on repeatable tasks.
- Use [[Fine-Tuning Artifact Index]] when reviewing adapters and checkpoints.

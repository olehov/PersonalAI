# Benchmarks

## Purpose

Benchmarking in PersonalAI exists to make model quality measurable.

It is used to compare:

- grounded coding answers
- repo-aware planning quality
- execution honesty
- continuation quality across turns
- vault-only versus web-grounded behavior

## Current Benchmark Assets

Located under `training_examples/benchmarks/`.

Key benchmark categories already in use:

- grounded coding answers
- multi-turn continuation
- repository analysis
- implementation scoping
- execution honesty
- web grounding comparison

## Current Capabilities

- load benchmark packs
- run individual benchmark tasks
- compare multiple models on the same tasks
- persist benchmark history in SQLite
- inspect benchmark history through CLI and UI flows

## Recent Coverage

The current benchmark system includes paired scenarios for:

- `vault-only`
- `forced web-grounded`

This gives PersonalAI a regression harness for freshness-sensitive requests instead of relying on ad hoc manual checks.

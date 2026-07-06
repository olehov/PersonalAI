
# PersonalAI Roadmap

## Related Notes

- [[Project Index]]
- [[Vision]]
- [[Architecture]]
- [[Technology Stack]]
- [[PersonalAI MVP Knowledge Map]]
- [[Benchmark Workflow Index]]
- [[Fine-Tuning Artifact Index]]
- [[Agent Runtime Cases Index]]

## Implementation Bridges

- current implementation subtree: [[PersonalAI MVP Knowledge Map]]
- benchmark and workflow validation: [[Benchmark Workflow Index]]
- fine-tuning and evaluation outputs: [[Fine-Tuning Artifact Index]]
- saved runtime and planning traces: [[Agent Runtime Cases Index]]

## Working Rule

Move through the roadmap deliberately and do not jump to later items until the current priority block is stable enough.

Default rule:

- finish the current step
- validate it
- record the result
- only then move to the next step

This roadmap is the current execution anchor for PersonalAI work.

## Current State

Already implemented:

- Obsidian vault reader
- in-memory knowledge index
- grounded retrieval and answer pipeline
- safe note draft and write pipeline
- maintenance workflow
- training corpus, eval, compare, and fine-tune bundle workflow
- local web UI and JS frontend
- SQLite history
- early agent runtime with:
  - retrieval
  - planning
  - action plan
  - action execution
- first safe agent adapters:
  - inspect_note
  - inspect_repo
  - draft_module
  - plan_validation

Current architectural position:

- the system is no longer only a knowledge assistant
- the system is becoming a local-first engineering agent platform
- the main next goal is to stabilize the agent runtime before adding deeper execution power

## Active Backlog

### P0 - Stabilize Agent Runtime

Goal:

- make the current agent runtime a reliable base layer for all future repo and coding workflows

Tasks:

- split agent-related code into a clearer package or module boundary
- define one stable tool registry contract
  - status: done
- define stable run and action statuses
  - status: done
- persist agent run artifacts, not only plain ask history
  - status: done
- make the runtime output easy to inspect from CLI, API, and UI
  - status: done
- avoid mixing simple Q&A history with agent runtime artifacts
  - status: done

Definition of done:

- runtime structure is clear
- artifacts are persisted
- statuses are explicit
- future adapters can be added without redesigning the core loop

### P1 - Expand Safe Adapters

Goal:

- increase useful execution without allowing unsafe autonomous mutation

Tasks:

- add `draft_module` adapter
  - status: done
- add file-tree inspection adapter
  - status: done
- add build-config inspection adapter
  - status: done
- add patch-planning adapter
  - status: done
- keep outputs as safe drafts or structured artifacts

Definition of done:

- agent can inspect and propose first-slice code work
- agent still does not falsely claim that files were edited or tests were run

### P1 - Repo-First Workflow

Goal:

- make PersonalAI useful on real project folders such as `Projects/Minishell`

Tasks:

- improve repository path resolution from request plus vault context
  - status: done
- generate first-slice implementation drafts from repo plus notes plus request
  - status: done
- derive validation plans from actual repository markers
  - status: done
- prepare safe patch or module drafts without direct mutation
  - status: done

Definition of done:

- `Agent` mode can analyze a real project and produce grounded repo-aware next actions

### P1 - Agent UI Maturation

Goal:

- make the runtime understandable and debuggable from the frontend

Tasks:

- show agent run timeline
- show steps, recommended actions, and executed actions separately
- add dedicated agent session history
  - status: done

Definition of done:

- agent runs are readable as process, not just as a final answer blob

### P1 - Workflow Routing

Goal:

- reduce manual mode selection by teaching the system to choose the right workflow automatically

Tasks:

- add backend intent routing for:
  - grounded Q&A
  - repo analysis
  - implementation planning
  - note drafting
  - status: done
- return routing decision metadata for debugging
  - status: done
- keep manual override in UI while routing is still maturing
  - status: done

Definition of done:

- the system can auto-select the main workflow for common requests
- routing decisions are inspectable when the classification is wrong

### P1 - Evaluation and Benchmarking

Goal:

- measure real usefulness on our actual workflows instead of only generic prompting quality

Tasks:

- create benchmark tasks for:
  - grounded coding answers
  - repository analysis
  - implementation scoping
  - first-slice code drafting
  - execution honesty
  - status: done
- log run artifacts for benchmark review
  - status: done
- compare models on planning quality and action quality
  - status: done
- expand Ukrainian supervised examples for language quality

Definition of done:

- model comparison is tied to actual PersonalAI tasks

### P2 - Controlled Execution Layer

Goal:

- move from planning-only and inspection-only agent behavior toward controlled action

Tasks:

- implement safe repo draft pipeline
- implement patch proposal flow
- add approval-gated mutation steps
- allow selected adapters to move from `deferred` to controlled execution

Definition of done:

- execution is explicit, reviewable, and approval-aware

## Sequence

Work in this order unless a blocker forces a small detour:

1. P0 - Stabilize Agent Runtime
2. P1 - Expand Safe Adapters
3. P1 - Repo-First Workflow
4. P1 - Agent UI Maturation
5. P1 - Workflow Routing
6. P1 - Evaluation and Benchmarking
7. P2 - Controlled Execution Layer

## Short Next Steps

The immediate next recommended steps are:

1. expand Ukrainian supervised examples for language quality
2. expand benchmark tasks for routing quality and workflow selection honesty
3. refine auto-routing heuristics against real query logs

## Phase 1

- Obsidian Vault
- Knowledge Structure
- Documentation

## Phase 2

- Ollama Integration
- Vector Search
- Knowledge Retrieval

## Phase 3

- Automatic Note Creation
- Automatic Note Updates
- Directory and Graph Analysis

## Phase 4

- Code Generation
- Repository Analysis
- Agent Loop
- Execution Observation

## Phase 5

- Autonomous Knowledge Refactoring
- Sandbox Execution
- Failure-Aware Tool Feedback

## Phase 6

- Engineering Assistant
- MCP Tool Integration
- Benchmark Harness
- Multi-Model Evaluation

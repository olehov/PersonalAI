# PersonalAI Architecture

## Core Documents

- [[Project Index]]
- [[Vision]]
- [[Roadmap]]
- [[PersonalAI MVP Knowledge Map]]
- [[Technology Stack]]
- [[Benchmark Workflow Index]]

## Implementation Bridges

- live implementation subtree: [[PersonalAI MVP Knowledge Map]]
- concrete component choices: [[Technology Stack]]
- benchmarked coding workflows: [[Benchmark Workflow Index]]

The current implementation map for these architectural layers lives in [[PersonalAI MVP Knowledge Map]], while repeatable workflow checks are grouped in [[Benchmark Workflow Index]].

## Behavioral Rules

- [[AI Behavior]]
- [[Knowledge Management]]
- [[Note Refactoring Rules]]

## Development Rules

- [[Coding Style]]

---

## High Level Architecture

```text
Obsidian
    ↓
Knowledge Base
    ↓
Vector Search
    ↓
Knowledge Engine
    ↓
Developer Agent
    ↓
Code Generation
```

---

## Components

### Obsidian

Stores all knowledge.

### Knowledge Engine

Responsible for:

- note creation
- note updates
- note linking
- note refactoring

### Developer Agent

Responsible for:

- code generation
- code analysis
- repository understanding
- architecture suggestions

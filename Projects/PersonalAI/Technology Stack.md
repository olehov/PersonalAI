
# Technology Stack

## Related Notes

- [[Project Index]]
- [[Architecture]]
- [[Roadmap]]
- [[Agent Smith Analysis]]
- [[PersonalAI MVP Knowledge Map]]
- [[Fine-Tuning Artifact Index]]
- [[Benchmark Workflow Index]]
- [[Agent Runtime Cases Index]]

## Implementation Bridges

- runtime-facing implementation subtree: [[PersonalAI MVP Knowledge Map]]
- evaluation and task scoring: [[Benchmark Workflow Index]]
- fine-tuned adapters and training artifacts: [[Fine-Tuning Artifact Index]]
- runtime traces and saved planning artifacts: [[Agent Runtime Cases Index]]

The live implementation subtree is currently organized through [[PersonalAI MVP Knowledge Map]], while evaluation and model comparison workflows are grouped in [[Benchmark Workflow Index]] and [[Fine-Tuning Artifact Index]].

## Core

### Python

Responsibilities:

- orchestration
- knowledge management
- agent runtime

This implementation surface is described concretely in [[PersonalAI MVP Overview]].

### Ollama

Responsibilities:

- local LLM inference

### Obsidian

Responsibilities:

- knowledge storage

### Agent Runtime

Responsibilities:

- thought-code-observation loop
- task state management
- termination control

### Sandbox

Responsibilities:

- controlled code execution
- timeout and path limits
- structured observation feedback

---

## Future

### Qdrant

Vector database.

### Open WebUI

User interface.

### Git

Version control.

### MCP

Tool integration layer.

### Benchmark Harness

Task evaluation and model comparison.

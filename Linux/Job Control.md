# Job Control

## Basics
Job control is the shell-level mechanism for managing foreground and background processes in an interactive terminal session.

## Core Concepts

- a foreground job receives terminal input directly
- a background job continues running while the shell prompt returns
- shells track jobs separately from raw process IDs

## Common Commands

### `jobs`
List current shell-managed jobs.

### `bg`
Resume a stopped job in the background.

### `fg`
Bring a background or stopped job into the foreground.

### `Ctrl+C`
Usually sends `SIGINT` to the foreground process group.

### `Ctrl+Z`
Usually suspends the foreground process and lets the shell manage it as a stopped job.

## Why It Matters
Job control builds directly on [[Processes and Signals]] and is useful when working with long-running commands, editors, debuggers, and SSH sessions.

## Related Notes

- [[Processes and Signals]]
- [[Systemd]]

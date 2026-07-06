# Pipes and Redirection

## Basics
Pipes and redirection are shell features for connecting command input and output streams.

## Redirection

### Standard Streams

- standard input: `stdin`
- standard output: `stdout`
- standard error: `stderr`

### Common Forms

- `>` write output to a file
- `>>` append output to a file
- `<` read input from a file
- `2>` redirect standard error

## Pipes
The pipe operator `|` sends the output of one command to the input of another command.

Examples:

- `ps aux | grep python`
- `journalctl -u nginx | less`

## Why It Matters
Pipes and redirection are essential for debugging running services, filtering logs, and composing CLI workflows around [[Processes and Signals]] and [[Systemd]].

## Related Notes

- [[Processes and Signals]]
- [[Systemd]]
- [[SSH]]
- [[Retries and Timeouts]]

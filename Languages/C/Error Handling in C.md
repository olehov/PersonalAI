# Error Handling in C

## Basics
C usually handles errors through return codes, output parameters, `errno`, and explicit cleanup paths.

## Return Conventions

- use `0` or a positive result for success only when the API is consistent
- use negative or enum-based error codes when multiple failure modes matter
- separate status from data when possible

## API Design

- document what each error code means
- validate inputs at the boundary of each function
- avoid partial side effects before the function can still fail

## Cleanup on Failure

- use one cleanup path for resources acquired in sequence
- release resources in reverse order of acquisition
- keep error labels short and predictable in low-level code

## `errno`

- use `errno` for system-call style failures when appropriate
- copy or translate `errno` quickly if later calls may overwrite it
- do not rely on `errno` when the function contract does not promise it

## Debuggability

- include enough context in logs to identify the failing resource or operation
- distinguish programmer errors from runtime failures
- make repeated retry behavior explicit to avoid hidden failure loops

## Related Notes

- [[C Best Practices]]
- [[Memory Management in C]]
- [[Memory Ownership Patterns in C]]
- [[Resource Lifetime and Cleanup in C]]
- [[Undefined Behavior in C]]
- [[Strings in C]]
- [[Command-Line Arguments in C]]
- [[Parsing and Validation in C]]
- [[File IO in C]]
- [[Build and Warnings in C]]
- [[Observability]]

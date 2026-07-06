# C Best Practices

## Basics
C code benefits from simple ownership rules, explicit error handling, conservative memory usage, and portable interfaces.

## Core Principles

- prefer clear ownership over implicit sharing
- keep APIs small and predictable
- check every function contract and return value
- optimize after correctness and measurements
- make undefined behavior hard to trigger

## Portability

- prefer standard C and standard library behavior over compiler-specific extensions
- be careful with integer sizes, alignment, and assumptions about platform ABI
- isolate OS-specific code behind small interfaces

## Memory Safety

- initialize data before use
- pair every allocation path with a clear release path
- size buffers explicitly and validate boundaries
- avoid pointer arithmetic when indexing is clearer

See [[Memory Management in C]].
See [[Pointers and Arrays in C]].

## Error Handling

- return explicit status codes
- document ownership and error semantics in the API
- fail early on invalid input
- log enough context to debug failures later

See [[Error Handling in C]].

## API Design

- pass only the data a function needs
- use `const` to mark read-only inputs
- avoid hidden global state in reusable code
- keep headers stable and minimal

See [[Header Design in C]].

## Common Pitfalls

- unchecked allocations
- buffer overflows and off-by-one errors
- dangling pointers after `free`
- double free and partial cleanup bugs
- mixing ownership responsibilities across modules
- assuming signed overflow or uninitialized data is safe

## Related Notes

- [[Memory Management in C]]
- [[Memory Ownership Patterns in C]]
- [[Error Handling in C]]
- [[Header Design in C]]
- [[Pointers and Arrays in C]]
- [[Command-Line Arguments in C]]
- [[File IO in C]]
- [[Undefined Behavior in C]]

# Memory Management in C

## Basics
Manual memory management in C requires explicit allocation, initialization, ownership tracking, and cleanup.

## Allocation Rules

- check the result of `malloc`, `calloc`, and `realloc`
- use `sizeof(*ptr)` style allocation to reduce type mismatch errors
- avoid overwriting the original pointer directly with `realloc` results

## Ownership

- decide which function allocates and which function frees
- document transfer of ownership in function contracts
- prefer one clear owner for each heap allocation

## Cleanup

- keep cleanup paths simple and centralized
- free partially initialized state on failure
- set pointers to `NULL` after `free` when the pointer may be reused

## Safer Patterns

- initialize structs to a known state before partial setup
- use length-aware operations for buffers and strings
- prefer stack allocation when lifetime and size are small and obvious

## Common Bugs

- leaking memory on early returns
- double free
- use-after-free
- writing past the end of a buffer
- losing the original allocation on failed `realloc`

## Related Notes

- [[C Best Practices]]
- [[Error Handling in C]]
- [[Header Design in C]]
- [[Memory Ownership Patterns in C]]
- [[Resource Lifetime and Cleanup in C]]
- [[Pointers and Arrays in C]]
- [[Undefined Behavior in C]]
- [[Strings in C]]

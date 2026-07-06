# Undefined Behavior in C

## Basics
Undefined behavior means the C standard imposes no requirements on what happens. Once a program executes undefined behavior, the result may vary by compiler, optimization level, input, or runtime environment.

## Common Sources

- reading uninitialized variables
- accessing memory outside object bounds
- dereferencing invalid, null, or dangling pointers
- signed integer overflow
- using pointers after `free`
- violating function contracts or object lifetime assumptions

## Why It Is Dangerous

- code may appear to work in one build and fail in another
- compiler optimizations may remove checks or reorder logic based on assumptions that undefined behavior never occurs
- bugs become hard to reproduce because behavior is not stable across environments
- security problems can hide behind seemingly rare memory errors

## Prevention Habits

- initialize data before use
- validate indices, lengths, and pointer preconditions at API boundaries
- keep ownership and cleanup rules explicit
- prefer simpler control flow over clever low-level tricks
- treat compiler warnings as bugs until understood
- test with multiple warning levels, sanitizers, and optimization settings

## Practical Focus Areas

- check array bounds and pointer arithmetic carefully
- avoid returning addresses of stack objects
- document buffer sizes and mutability in function signatures
- keep `realloc` and partial-cleanup paths explicit

## Debuggability

- log enough context to identify the failing buffer, pointer, or size assumption
- reduce hidden side effects before failure paths
- isolate suspicious low-level code so it can be tested independently

## Related Notes

- [[C Best Practices]]
- [[Memory Management in C]]
- [[Pointers and Arrays in C]]
- [[Error Handling in C]]
- [[Strings in C]]
- [[Binary Data and Endianness in C]]
- [[Struct Layout and Serialization in C]]
- [[Build and Warnings in C]]

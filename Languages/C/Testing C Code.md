# Testing C Code

## Basics

Testing C code requires more than checking the happy path. Low-level modules benefit from explicit edge-case tests, warning-clean builds, sanitizer runs, and small interfaces that make failure behavior observable.

## Unit Boundaries

- keep parsing, allocation, and I/O boundaries small enough to test in isolation
- prefer functions with explicit inputs and outputs over hidden global state
- separate pure logic from OS interaction when practical
- design APIs so invalid input and runtime failure can be asserted directly

These habits reinforce the interface discipline in [[C Best Practices]] and [[Header Design in C]].

## Edge Cases

- test zero lengths, empty strings, maximum sizes, and partial initialization
- test invalid input, truncation, and cleanup on mid-function failure
- test repeated calls that exercise ownership and reuse rules
- test boundary values for counters, offsets, and integer conversions

## Build and Runtime Checks

- run with strict warnings enabled and treat new warnings as failures
- use address and undefined-behavior sanitizers regularly
- test both debug-friendly and optimized builds because optimization can expose hidden assumptions
- keep regression cases for bugs that previously reached production

See [[Build and Warnings in C]] and [[Undefined Behavior in C]].

## Harness Design

- keep fixtures simple and cleanup explicit
- avoid tests that depend on environment quirks unless the behavior under test is platform-specific
- use helper functions to reduce duplication, but keep assertions close to the scenario
- make failure messages identify the exact buffer, size, or API contract that broke

## Testing Failure Paths

- simulate allocation failure where practical
- test short reads, short writes, and malformed input for parsing code
- verify resources are released on every early return path
- check that status codes and output state remain consistent after failure

Failure-path tests pair naturally with [[Error Handling in C]], [[Parsing and Validation in C]], and [[Resource Lifetime and Cleanup in C]].

## Related Notes

- [[C Best Practices]]
- [[Build and Warnings in C]]
- [[Undefined Behavior in C]]
- [[Error Handling in C]]
- [[Parsing and Validation in C]]
- [[Resource Lifetime and Cleanup in C]]

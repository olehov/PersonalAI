# Strings in C

## Basics
C strings are byte arrays terminated by `'\0'`. Correct code must account for terminators, buffer size, ownership, and the fact that most string APIs rely on conventions rather than explicit length metadata.

## Null Termination

- a valid C string must contain a terminating `'\0'`
- missing termination can turn ordinary reads into out-of-bounds access
- string literals are terminated automatically, but copied or formatted data still needs verification

## Buffer Sizing

- allocate space for content plus the terminating byte
- pass explicit buffer lengths to APIs whenever possible
- treat truncation as a behavior to detect, not something to ignore
- avoid assuming fixed-size buffers are large enough for future inputs

## Copying and Formatting Risks

- unchecked `strcpy`, `strcat`, and `sprintf` style calls can overflow buffers
- formatted output must account for both data length and terminator
- overlapping source and destination buffers can produce incorrect results
- copying from untrusted input requires length validation before the copy

## Ownership Boundaries

- stack-backed string buffers must not escape their lifetime
- pointers to string data do not imply ownership by themselves
- APIs should document who allocates, who writes, and who frees any heap-backed string
- mutable buffers and read-only string views should stay distinct in function contracts

## Prevention Habits

- initialize buffers before partial use when later code depends on termination
- keep size calculations close to allocation and copy sites
- prefer bounded APIs and check their return values
- validate indices, offsets, and format inputs at API boundaries
- test string-heavy code with warnings, sanitizers, and edge-case inputs

## Practical Focus Areas

- distinguish byte capacity from current string length
- avoid returning pointers to temporary or stack-allocated buffers
- keep cleanup paths explicit when string buffers are reallocated or built incrementally
- make truncation and formatting failure visible to callers

## Related Notes

- [[Memory Management in C]]
- [[Pointers and Arrays in C]]
- [[Undefined Behavior in C]]
- [[Error Handling in C]]
- [[Command-Line Arguments in C]]
- [[Parsing and Validation in C]]
- [[Memory Ownership Patterns in C]]
- [[File IO in C]]
- [[Build and Warnings in C]]

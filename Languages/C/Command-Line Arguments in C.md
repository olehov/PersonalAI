# Command-Line Arguments in C

## Basics
Programs in C usually receive command-line input through `int argc, char **argv` or equivalent parameter forms. Correct code must validate argument count, parse text carefully, and report usage errors without leaving ambiguous program state.

## `argc` and `argv`

- `argc` tells the program how many argument strings are available
- `argv` points to an array of character pointers, where each entry is a C string
- `argv[0]` is usually the program name or invocation path
- code must not assume optional arguments exist before checking `argc`

## Validation

- check argument count before reading positional parameters
- reject malformed combinations early instead of continuing with partial assumptions
- keep usage rules explicit when flags, paths, or numeric values are required
- make failure paths easy to follow when several arguments depend on each other

## Parsing Strings and Numbers

- treat every command-line argument as untrusted text until validated
- use string comparisons carefully and document accepted spellings or modes
- prefer conversion functions that expose parse failures instead of silently accepting bad input
- check for trailing junk, overflow, and missing values when converting numeric arguments

See [[Strings in C]].

## Error Handling

- print clear usage messages when required arguments are missing
- distinguish invalid input from runtime failures such as file-open errors
- keep return codes consistent so shell scripts can detect failure reliably
- preserve enough context to explain which argument or conversion failed

See [[Error Handling in C]].

## Ownership and Lifetime

- argument strings are provided by the runtime and are not owned by application cleanup code
- do not write into argument strings unless the program contract and platform behavior are clearly understood
- copy argument data into owned buffers only when mutation or long-term storage is required
- document whether downstream code borrows an argument string or makes its own copy

## Practical Habits

- centralize argument parsing when the program has multiple modes or flags
- keep default values explicit instead of relying on uninitialized state
- combine argument validation with warnings, tests, and edge-case examples
- keep parsing code separate from core business logic when that makes failure handling clearer

## Related Notes

- [[C Best Practices]]
- [[Parsing and Validation in C]]
- [[Strings in C]]
- [[Error Handling in C]]
- [[Pointers and Arrays in C]]
- [[Build and Warnings in C]]
- [[File IO in C]]

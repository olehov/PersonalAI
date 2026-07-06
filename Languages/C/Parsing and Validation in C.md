# Parsing and Validation in C

## Basics
Parsing in C means turning untrusted text or binary input into validated program data. Correct code must separate raw input handling from semantic validation, report failures clearly, and avoid letting partially parsed state leak into normal control flow.

## Input Boundaries

- treat command-line arguments, files, environment variables, and network data as untrusted input
- define which syntax and ranges are accepted before writing parsing code
- distinguish "cannot parse" from "parsed successfully but value is invalid"
- keep boundary checks close to the first point where external data enters the program

## String and Numeric Parsing

- prefer conversion functions that expose where parsing stopped
- check for empty input, trailing junk, overflow, underflow, and missing delimiters
- validate numeric ranges after conversion instead of assuming the target type is safe
- keep size and length checks explicit when parsing strings, tokens, or buffers

See [[Strings in C]].

## Validation Rules

- validate required fields before using partially parsed objects
- keep format rules explicit when several fields depend on each other
- reject malformed combinations early instead of trying to recover silently
- separate syntax checks from higher-level semantic rules when that makes failures clearer

## Error Reporting

- return enough context to explain which field, token, or offset failed
- keep parse errors distinct from runtime failures such as allocation or file-open errors
- avoid losing the original failure cause when several validation steps run in sequence
- make caller-visible usage or error messages precise enough to support debugging

See [[Error Handling in C]].

## Partial State and Cleanup

- do not expose partially initialized objects as if parsing had succeeded
- free temporary allocations on failed parse paths
- keep one visible cleanup path when parsing acquires several helper buffers or resources
- make success and failure ownership rules explicit for parsed output objects

## Practical Habits

- parse into temporary variables first when validation may still fail
- centralize repeated token or field checks when the same format appears in several places
- test edge cases such as empty input, whitespace, truncation, overflow, and invalid separators
- combine parsing code with warnings, sanitizers, and negative tests, not only happy-path examples

## Related Notes

- [[Command-Line Arguments in C]]
- [[Binary Data and Endianness in C]]
- [[Strings in C]]
- [[Error Handling in C]]
- [[File IO in C]]
- [[Memory Ownership Patterns in C]]
- [[Build and Warnings in C]]

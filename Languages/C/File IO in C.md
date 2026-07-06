# File I/O in C

## Basics
C file I/O usually goes through `FILE *` handles and the standard library in `stdio.h`. Correct code must handle open failures, partial reads or writes, buffering behavior, and cleanup on every path.

## Opening and Closing Files

- check the result of `fopen` before using the handle
- choose the mode string deliberately, for example read, write, append, or update
- close every successfully opened file with `fclose`
- treat `fclose` as a fallible operation when buffered writes still need to reach the OS

## Text and Binary Modes

- text mode may apply platform-specific newline translation
- binary mode is safer for structured data, byte-exact formats, and non-text payloads
- do not assume text and binary behavior are interchangeable across platforms
- document the expected file format in the API contract

## Reads and Writes

- check how many items `fread` or `fwrite` actually processed
- partial reads can be normal near end of file, but partial writes usually need explicit handling
- loops that process streams should distinguish successful progress from failure and end-of-file
- treat zero-length progress carefully to avoid infinite retry loops

## Error Handling

- check `ferror` and `feof` instead of guessing why a read stopped
- preserve enough context to explain which path, operation, or offset failed
- keep cleanup explicit when a later read or write fails after earlier allocations
- do not lose the original failure cause by overwriting `errno` or status codes too early

See [[Error Handling in C]].

## Buffering and Flushing

- standard I/O is usually buffered, which affects visibility and performance
- call `fflush` when the program must force buffered output before normal close
- do not assume buffered output reached disk just because `fprintf` succeeded
- be careful when mixing buffered stdio with lower-level descriptor I/O on the same file

## Portability and Data Layout

- binary file formats must not rely on compiler-specific struct layout by accident
- integer width, endianness, padding, and alignment matter for portable on-disk data
- prefer explicit serialization for data that crosses machines, compilers, or architectures
- keep file format assumptions close to the code that reads and writes them

## Practical Habits

- separate file-open logic from parse or processing logic when it makes cleanup clearer
- keep buffer sizes explicit and validate them before each read or formatted write
- test failure paths such as missing files, short reads, full disks, and permission errors
- use warnings and sanitizers to catch adjacent bugs around buffers, strings, and cleanup

## Related Notes

- [[C Best Practices]]
- [[Error Handling in C]]
- [[Strings in C]]
- [[Command-Line Arguments in C]]
- [[Parsing and Validation in C]]
- [[Binary Data and Endianness in C]]
- [[Struct Layout and Serialization in C]]
- [[Resource Lifetime and Cleanup in C]]
- [[Memory Management in C]]
- [[Build and Warnings in C]]
- [[Undefined Behavior in C]]

# Build and Warnings in C

## Basics
Safe C builds rely on strict warnings, separate debug and optimized configurations, and regular sanitizer runs. Build settings should help surface bugs early instead of hiding them behind permissive defaults.

## Warning Levels

- enable broad warning sets such as `-Wall` and `-Wextra`
- add targeted warnings that matter for pointer, format, and conversion mistakes
- keep warning flags consistent across local builds and CI
- review newly introduced warnings instead of normalizing them away

## Treat Warnings as Bugs

- treat warnings as failures until they are understood
- avoid merging code that compiles only because warnings are ignored
- fix root causes instead of silencing diagnostics prematurely
- pay special attention to uninitialized data, format mismatches, and narrowing conversions

## Debug and Optimized Builds

- use debug builds to preserve debuggability and make sanitizer output easier to interpret
- test optimized builds separately because optimization can expose hidden undefined behavior
- verify that code behaves correctly under both low-optimization and production-like settings
- avoid assuming a bug that disappears in debug mode is harmless

## Sanitizers

- use address sanitizers to catch invalid accesses, use-after-free, and double free
- use undefined behavior sanitizers to catch arithmetic and lifetime violations
- run sanitizer-enabled builds regularly in tests, not only after a failure is suspected
- treat sanitizer findings as code bugs, not tooling noise

## Repeatable Build Habits

- keep compiler, flags, and build steps explicit in scripts or build files
- avoid hidden environment assumptions between developer machines and CI
- make warning and sanitizer configurations easy to run locally
- test with multiple optimization settings when debugging low-level failures

## Practical Focus Areas

- combine warnings with strict review of pointer, buffer, and format usage
- check that string and buffer APIs are always called with correct sizes
- keep release builds reproducible enough that failures can be compared across environments
- log compiler and sanitizer context when investigating build-specific bugs

## Related Notes

- [[Undefined Behavior in C]]
- [[Strings in C]]
- [[Memory Management in C]]
- [[Pointers and Arrays in C]]
- [[Error Handling in C]]
- [[File IO in C]]
- [[Struct Layout and Serialization in C]]

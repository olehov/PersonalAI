# Binary Data and Endianness in C

## Basics
Binary data handling in C depends on byte order, field size, alignment assumptions, and the difference between in-memory representation and external format. Correct code must treat host layout and serialized layout as separate concerns.

## Byte Order

- little-endian systems store the least significant byte at the lowest address
- big-endian systems store the most significant byte at the lowest address
- code that inspects or serializes multi-byte values must not assume one byte order unless the format defines it
- host byte order is an implementation detail, not a portable file or network contract

## Host Format vs External Format

- in-memory representation is optimized for the local machine, not for portability
- file formats and wire protocols should define byte order explicitly
- the same numeric value may need conversion before writing or after reading
- raw memory dumps are not a substitute for a stable binary format

## Fixed-Width Types

- prefer fixed-width integer types when exact field size matters
- do not assume `int`, `long`, or pointer size is stable across targets
- keep field size assumptions close to the serialization code
- document width and signedness rules when binary compatibility matters

## Parsing Binary Input

- validate buffer length before reading fields from binary input
- decode fields in the format's defined byte order instead of trusting host layout
- advance through input deliberately so partial records cannot be mistaken for complete ones
- reject malformed or truncated data instead of continuing with partially decoded state

See [[Parsing and Validation in C]].

## Portability Risks

- byte order, padding, and alignment can all break naive binary interchange
- copying raw structs across machines can silently produce invalid data
- binary parsing code that ignores width or offset checks can drift into undefined behavior
- tests should include cross-platform or synthetic byte-order cases when compatibility matters

## Practical Habits

- keep encode and decode logic close to the format definition
- use explicit conversions instead of relying on implicit representation
- separate transport or file format structures from ordinary in-memory business structs
- combine binary parsing with warnings, sanitizers, and negative tests for malformed input

## Related Notes

- [[File IO in C]]
- [[Struct Layout and Serialization in C]]
- [[Parsing and Validation in C]]
- [[Undefined Behavior in C]]
- [[Build and Warnings in C]]

# Struct Layout and Serialization in C

## Basics
Struct layout in C depends on member order, alignment requirements, padding, and platform conventions. Raw binary serialization is risky unless the code controls layout assumptions explicitly and treats portability as part of the format design.

## Padding and Alignment

- compilers may insert padding between members to satisfy alignment requirements
- member order affects struct size and memory layout
- identical-looking structs can still differ across compilers, architectures, or ABI settings
- alignment assumptions that seem harmless in memory can become bugs once data crosses process or machine boundaries

## Endianness

- multi-byte integers and other binary fields may be stored in different byte orders on different systems
- raw memory dumps do not automatically normalize endianness
- binary protocols and file formats should define byte order explicitly
- code that reads external binary data must convert fields deliberately instead of assuming host layout matches the format

## Why Raw Struct Dumps Are Risky

- writing a struct directly with `fwrite` can capture padding bytes as well as real fields
- uninitialized padding may leak unstable or meaningless data
- future source changes that reorder members can silently break compatibility
- a raw struct image may stop being valid when compiler flags, architecture, or data model changes

See [[File IO in C]].

## Explicit Serialization

- serialize fields one by one when portability matters
- make field sizes, byte order, and optional sections part of the format contract
- validate record length and parse progress on input instead of trusting binary layout implicitly
- keep encode and decode logic close to the format definition so changes stay visible

## Relationship to Undefined Behavior

- reading binary data into the wrong type or assuming invalid alignment can trigger undefined behavior
- pointer casts over packed or foreign binary layouts need extra care
- padding and lifetime assumptions become dangerous when low-level code treats memory as if layout were universal
- sanitizer and warning coverage can catch some nearby bugs, but format discipline still matters

See [[Undefined Behavior in C]].

## Practical Habits

- use fixed-width integer types when the binary format depends on exact field size
- document versioning and compatibility rules for on-disk or on-wire formats
- separate transport encoding from in-memory business structs when the format must stay stable
- test serialization across different builds, architectures, or compiler settings when portability matters

## Related Notes

- [[C Best Practices]]
- [[Binary Data and Endianness in C]]
- [[File IO in C]]
- [[Pointers and Arrays in C]]
- [[Undefined Behavior in C]]
- [[Build and Warnings in C]]

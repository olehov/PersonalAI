# Integer Types and Conversions in C

## Basics

Correct C code depends on knowing the width, signedness, and conversion rules of integer types. Many low-level bugs come from silent promotions, narrowing conversions, overflow assumptions, and mixing signed with unsigned values.

## Choosing Types

- use `size_t` for object sizes and array lengths
- use fixed-width integers such as `uint32_t` only when exact width matters
- use plain `int` for ordinary loop counters and arithmetic when no stronger requirement exists
- document assumptions when a value crosses an API, file format, or network boundary

## Integer Promotions

- smaller integer types are usually promoted to `int` or `unsigned int` before arithmetic
- expressions involving mixed signedness can change meaning unexpectedly
- do not assume `char` is signed or unsigned on every platform
- review comparisons carefully when one operand came from a size or count

## Signed and Unsigned Mixing

- avoid comparing signed values directly with `size_t` or other unsigned counts
- convert deliberately after validating range
- prefer one representation for related values inside the same function
- treat compiler warnings about signedness as real bugs until understood

## Narrowing and Overflow

- do not assume signed overflow wraps predictably; that can become [[Undefined Behavior in C]]
- validate range before casting from a wider type to a narrower type
- keep parsing and boundary checks close to the conversion site
- use explicit limits such as `INT_MAX`, `UINT32_MAX`, or documented protocol bounds

## Boundary-Sensitive Code

- integer choices matter for buffer sizes, offsets, binary formats, and serialization
- keep host arithmetic separate from on-disk or on-wire layout rules
- convert once at the boundary and document the invariant afterward
- combine conversion review with warnings and sanitizer-friendly builds from [[Build and Warnings in C]]

## Practical Habits

- keep units explicit when a value represents bytes, elements, or milliseconds
- avoid sentinel values that rely on wrapping or implementation quirks
- prefer helper functions for repeated checked conversions
- test extreme values, negative inputs, and truncation paths explicitly

## Related Notes

- [[C Best Practices]]
- [[Undefined Behavior in C]]
- [[Build and Warnings in C]]
- [[Binary Data and Endianness in C]]
- [[Struct Layout and Serialization in C]]
- [[Parsing and Validation in C]]

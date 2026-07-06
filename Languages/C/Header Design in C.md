# Header Design in C

## Basics
Good C headers expose stable interfaces, minimize dependencies, and make ownership and mutability obvious.

## Structure

- keep declarations in headers and definitions in source files
- include only what is required by the public interface
- prefer forward declarations when full type definitions are not needed

## Interface Clarity

- use descriptive type and function names
- mark read-only pointer parameters as `const`
- document who owns returned pointers and who must free them

## Dependency Control

- avoid leaking internal implementation details into public headers
- keep macro usage narrow and well named
- reduce transitive includes to improve compile times and coupling

## Include Safety

- use include guards or `#pragma once`
- make headers safe to include from multiple translation units
- ensure a header can compile after being included on its own

## Common Mistakes

- exposing internal struct layout without a reason
- putting non-`static` function definitions in headers
- depending on include order
- using macros where typed constants or functions are clearer

## Related Notes

- [[C Best Practices]]
- [[Memory Management in C]]
- [[Pointers and Arrays in C]]
- [[Coding Style]]

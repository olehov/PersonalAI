# Memory Ownership Patterns in C

## Basics
Ownership in C means deciding which part of the program is responsible for allocating, mutating, transferring, and freeing a resource. Clear ownership rules reduce leaks, double free bugs, and ambiguous cleanup paths.

## Owned and Borrowed Pointers

- an owned pointer is responsible for eventually releasing the resource it references
- a borrowed pointer may be used temporarily but must not free the resource
- the same raw pointer type can represent either role, so the contract must be documented explicitly
- callers should not guess ownership from naming alone when the API can state it directly

## Transfer of Ownership

- ownership transfer should happen at clear API boundaries
- a function that takes ownership must say whether the caller may still read, mutate, or free the original resource
- a function that returns newly allocated memory must document that the caller is now responsible for cleanup
- partial transfer rules are risky unless they are narrow and explicit

## Cleanup Conventions

- keep one cleanup path for resources acquired in sequence
- release resources in reverse order of successful acquisition
- make ownership changes visible in code instead of hiding them behind side effects
- set reused pointers to `NULL` only when that actually helps prevent accidental reuse

See [[Error Handling in C]].

## API Contracts

- document who allocates and who frees every heap-backed object or buffer
- document whether returned pointers remain valid after later API calls
- distinguish mutable borrowed views from owned writable buffers
- avoid APIs that silently retain caller-owned pointers without saying so

## Common Ownership Bugs

- leaking memory on early return or partial initialization failure
- double free when two code paths both believe they own the same object
- use-after-free when borrowed references outlive the real owner
- losing ownership after `realloc` misuse or pointer reassignment
- freeing stack or static storage through an API that expected heap ownership

## Practical Habits

- choose one obvious owner for each heap allocation
- keep allocation and release rules close to the code that uses them
- prefer explicit init and destroy pairs for multi-step objects
- test failure paths where ownership changes are most likely to become unclear

## Related Notes

- [[Memory Management in C]]
- [[Error Handling in C]]
- [[Resource Lifetime and Cleanup in C]]
- [[Pointers and Arrays in C]]
- [[Strings in C]]
- [[C Best Practices]]
- [[Build and Warnings in C]]

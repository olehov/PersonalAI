# Resource Lifetime and Cleanup in C

## Basics
Resource lifetime in C means defining when an object becomes valid, who may use it, and exactly when cleanup must happen. Clear lifetime boundaries reduce leaks, use-after-free bugs, partial cleanup mistakes, and unclear failure handling.

## Lifetime Boundaries

- initialize objects into a known state before first use
- define when a resource becomes fully acquired and safe to expose to other code
- avoid letting partially initialized objects escape their setup path
- document when a pointer, handle, or buffer stops being valid

## Acquisition Order

- acquire dependent resources in a deliberate sequence
- keep the acquisition order visible when later cleanup depends on it
- avoid hidden ownership transitions inside helpers unless the contract makes them explicit
- prefer simple setup steps over tangled initialization with scattered side effects

## Reverse-Order Cleanup

- release resources in reverse order of successful acquisition
- keep one cleanup path when several resources are acquired in sequence
- make it obvious which resources are live at each failure point
- avoid duplicate cleanup logic across several return branches

See [[Error Handling in C]].

## Partial Failure Paths

- handle setup failures after each acquisition step instead of waiting until the end
- free only the resources that were actually acquired
- keep partially initialized structs in a state that destroy logic can handle safely
- treat cleanup after failed initialization as part of normal control flow, not as an afterthought

## Explicit Init and Destroy Logic

- use explicit init and destroy pairs when objects require multi-step setup
- keep destroy functions tolerant of empty or partially initialized state when practical
- separate ownership of embedded resources from borrowing of external references
- avoid implicit cleanup assumptions that depend on call order being “obvious”

## Practical Habits

- centralize cleanup labels or destroy helpers for low-level code with multiple resources
- pair each acquisition site with a visible release rule
- test early-return and failure paths as seriously as success paths
- combine lifetime discipline with warnings and sanitizers to catch misuse faster

## Related Notes

- [[Memory Ownership Patterns in C]]
- [[Memory Management in C]]
- [[Error Handling in C]]
- [[File IO in C]]
- [[Pointers and Arrays in C]]
- [[Build and Warnings in C]]

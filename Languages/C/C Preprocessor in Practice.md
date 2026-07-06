# C Preprocessor in Practice

## Overview

The C preprocessor performs textual transformation before compilation. Use it for header inclusion, compile-time feature selection, and small compile-time constants. Keep preprocessor logic narrow because macro expansion bypasses type checking, debugging is harder, and mistakes can lead to subtle portability or correctness problems.

## Macros

- Prefer `static inline` functions when type checking, single evaluation, or debugger visibility matter.
- Keep object-like macros simple and side-effect free.
- Parenthesize every macro parameter use and usually the whole expansion.
- Avoid passing expressions with side effects to function-like macros.

```c
#define ARRAY_COUNT(arr) (sizeof(arr) / sizeof((arr)[0]))
#define MAX(a, b) ((a) > (b) ? (a) : (b))
```

`MAX(x++, y++)` is still dangerous because each argument may be evaluated more than once. Parentheses help precedence, but they do not solve double evaluation.

## Function-Like Macro Traps

- Double evaluation:

```c
#define SQUARE(x) ((x) * (x))
int n = 3;
int value = SQUARE(n++); /* undefined or unintended behavior */
```

- Statement-like macros can break `if` / `else` control flow if they expand to multiple statements without a wrapper.
- Macros do not obey normal scope rules and can collide with identifiers from headers or other modules.
- Token pasting and stringification are powerful, but they increase complexity quickly and should stay local and well documented.

Use the `do { ... } while (0)` pattern for multi-statement macros:

```c
#define LOG_ERROR(msg)            \
    do {                          \
        fprintf(stderr, "%s\n", (msg)); \
    } while (0)
```

## Include Guards

- Every public header should have an include guard.
- Use a project-scoped, collision-resistant macro name.
- Keep headers self-contained: a header should compile when included into an otherwise empty translation unit if its dependencies are also available.

```c
#ifndef PERSONAL_AI_RING_BUFFER_H
#define PERSONAL_AI_RING_BUFFER_H

/* declarations */

#endif
```

Include guards prevent repeated parsing of the same declarations, but they do not fix poor dependency boundaries. That design work belongs in [[Header Design in C]].

## Conditional Compilation

- Use `#if`, `#ifdef`, and `#ifndef` for platform features, build modes, and optional integrations.
- Prefer feature-oriented names such as `HAVE_EPOLL` over vague names such as `LINUX_MODE`.
- Keep conditional branches small and local; large `#ifdef` trees are difficult to reason about and test.
- If one branch must never compile in a given build, fail early with `#error`.

```c
#if defined(HAVE_EPOLL)
/* epoll implementation */
#elif defined(HAVE_KQUEUE)
/* kqueue implementation */
#else
#error "No supported event backend configured."
#endif
```

When build flags alter behavior, make the invariants explicit and keep error paths consistent with [[Error Handling in C]].

## Common Traps

- Defining macros with common names such as `min`, `max`, or `DEBUG`.
- Hiding allocation, cleanup, or control flow inside complex macros.
- Depending on evaluation order inside macro arguments.
- Using macros where `enum`, `const`, or `static inline` would be clearer.
- Letting platform-specific `#ifdef` blocks spread across unrelated files.

Macro misuse often overlaps with the broader hazards described in [[Undefined Behavior in C]] and the review discipline from [[C Best Practices]].

## Related Notes

- [[C Best Practices]]
- [[Header Design in C]]
- [[Error Handling in C]]
- [[Undefined Behavior in C]]

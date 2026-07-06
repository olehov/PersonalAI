# Opaque Pointers and Handles in C

## Basics

Opaque pointers let a C API expose a type name without exposing the full struct layout. This keeps implementation details private, reduces coupling, and gives the module room to evolve without breaking callers.

## Why Use Opaque Types

- hide internal fields that callers should not depend on
- keep headers smaller and more stable
- separate public API design from private implementation details
- make ownership boundaries easier to document

## Typical Pattern

Public header:

```c
typedef struct ring_buffer ring_buffer_t;

ring_buffer_t *ring_buffer_create(size_t capacity);
void ring_buffer_destroy(ring_buffer_t *buffer);
```

Implementation file:

```c
struct ring_buffer {
    size_t capacity;
    size_t head;
    size_t tail;
    unsigned char *storage;
};
```

This pattern fits naturally with the interface discipline from [[Header Design in C]].

## Ownership and Lifetime

- document who creates, borrows, and destroys the handle
- make destroy functions safe on `NULL` only if the API contract says so
- define whether functions return owned pointers, borrowed pointers, or status codes
- keep cleanup paths consistent with [[Resource Lifetime and Cleanup in C]]

Opaque handles do not remove the need for explicit ownership rules; they only hide representation. The lifetime policy still belongs in the API contract and related code, as discussed in [[Memory Ownership Patterns in C]].

## Error Handling

- return clear status when creation or initialization fails
- avoid exposing half-initialized handles to callers
- separate allocation failure from misuse or invalid input when practical
- keep error contracts easy to use with [[Error Handling in C]]

## Tradeoffs

- callers cannot stack-allocate the hidden struct directly
- debugging may require helper accessors or targeted logging
- excessive accessor layering can make simple code harder to follow
- opaque types are less useful when the data must be trivially embedded by value

## Good Fit

- reusable libraries
- stateful parsers or protocol objects
- queues, buffers, allocators, and subsystem contexts
- modules that need ABI stability or strict representation control

## Related Notes

- [[Header Design in C]]
- [[Memory Ownership Patterns in C]]
- [[Resource Lifetime and Cleanup in C]]
- [[Memory Management in C]]
- [[Error Handling in C]]
- [[C Best Practices]]

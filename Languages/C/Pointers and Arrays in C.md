# Pointers and Arrays in C

## Basics
Pointers and arrays are closely related in C, but they are not interchangeable types. Arrays provide contiguous storage. Pointers store addresses and can refer to array elements, heap allocations, or standalone objects.

## Pointer Decay

- in most expressions, an array value decays to a pointer to its first element
- decay does not happen when applying `sizeof`, unary `&`, or when initializing an array object
- after decay, length information is no longer available from the pointer alone

## Indexing and Addressing

- `arr[i]` is equivalent to `*(arr + i)`
- pointer arithmetic advances by element size, not by bytes
- indexing is often clearer than manual pointer arithmetic for ordinary traversal
- multidimensional arrays need the correct element type to preserve row layout

## Function Parameters

- `int arr[]` and `int *arr` mean the same thing in a function parameter list
- pass an explicit length with any array-like input
- use `const` for read-only buffers to make mutability obvious
- document whether the function may retain, modify, or only read the pointed-to data

## Ownership Boundaries

- stack arrays are owned by the current scope and must not be returned by address
- pointers do not imply ownership on their own
- define which function allocates and which function frees any heap-backed buffer
- keep borrowed pointers and owned pointers conceptually separate in APIs

## Common Pitfalls

- assuming a pointer still knows the original array length
- returning pointers to stack-allocated arrays or local variables
- writing past the end of a buffer through incorrect index math
- mixing pointer traversal with unclear ownership and cleanup rules
- treating arrays and pointers as identical in all contexts

## Related Notes

- [[C Best Practices]]
- [[Memory Management in C]]
- [[Header Design in C]]
- [[Error Handling in C]]
- [[Command-Line Arguments in C]]
- [[Memory Ownership Patterns in C]]
- [[Struct Layout and Serialization in C]]
- [[Undefined Behavior in C]]
- [[Strings in C]]

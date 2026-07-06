# Priority Queue

## Basics
A priority queue is an abstract data type where each element has a priority, and removal returns the element with the highest or lowest priority rather than strict insertion order.

## Typical Implementation
The most common implementation uses a [[Heap]] because it provides efficient insertion and extraction of the top-priority element.

## Core Operations

### Insert
Add a new element with its priority.

Time complexity with a [[Heap]]: `O(log n)`.

### Peek
Return the current highest-priority or lowest-priority element without removing it.

Time complexity with a [[Heap]]: `O(1)`.

### Extract
Remove and return the top-priority element.

Time complexity with a [[Heap]]: `O(log n)`.

## Common Use Cases

- task scheduling
- Dijkstra-style graph algorithms
- event simulation
- best-first search
- search optimizations that may also appear alongside [[Binary Search]] in interview-style problem solving
- shortest-path algorithms such as [[Dijkstra]]

## Related Notes

- [[Heap]]
- [[Heapsort]]
- [[Binary Search]]
- [[Dijkstra]]
- [[Queues and Backpressure]]
- [[Caching]]

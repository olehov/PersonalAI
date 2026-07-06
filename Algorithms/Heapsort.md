# Heapsort

## Basics
Heapsort is a comparison-based sorting algorithm that uses a [[Heap]] to repeatedly extract the next maximum or minimum element.

## High-Level Idea

1. Build a heap from the input array.
2. Repeatedly move the root element to the end of the array.
3. Restore the heap property after each extraction.

## Complexity

- build heap: `O(n)`
- repeated extraction: `O(n log n)`
- overall: `O(n log n)`
- extra space: `O(1)` for in-place variants

## Tradeoffs

- guaranteed `O(n log n)` worst-case time
- not stable by default
- often slower in practice than quicksort on average data

## Related Notes

- [[Heap]]
- [[Priority Queue]]

# Binary Search

## Basics
Binary search finds a target value in a sorted collection by repeatedly dividing the search interval in half.

## Preconditions

- the input must be sorted according to the comparison being used
- random access is usually assumed for efficient midpoint checks

## High-Level Idea

1. Compare the target with the middle element.
2. If equal, return success.
3. If the target is smaller, continue in the left half.
4. If the target is larger, continue in the right half.

## Complexity

- time: `O(log n)`
- extra space: `O(1)` for the iterative variant

## Common Pitfalls

- overflow when computing the midpoint in low-level languages
- incorrect loop boundaries
- using binary search on unsorted data

## Related Notes

- [[Priority Queue]]
- [[Dynamic Programming]]

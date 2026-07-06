# Heap
===============

## Basics
Heap is a specialized tree-based data structure that satisfies the heap property: the parent node is either greater than (in a max-heap) or less than (in a min-heap) its child nodes. This property allows for efficient insertion and removal of elements.

### Min-Heap vs Max-Heap

* **Min-Heap**: The parent node is less than or equal to its child nodes. When the heap is extracted, the smallest element is returned.
* **Max-Heap**: The parent node is greater than or equal to its child nodes. When the heap is extracted, the largest element is returned.

## Common Operations

### Insertion
Insert a new element into the heap, maintaining the heap property. Time complexity: O(log n).

### Extraction
Remove and return the minimum (or maximum) element from the heap. Time complexity: O(log n).

### Decrease-Key
Decrease the value of an existing node in the heap, without violating the heap property. Time complexity: O(log n).

## Complexity

* Insertion: O(log n)
* Extraction: O(log n)
* Decrease-Key: O(log n)

## Common Use Cases

### Priority Queue
Heaps are often used as [[Priority Queue|priority queues]], where elements with higher priorities are extracted first.

### Heapsort
The [[Heapsort]] algorithm uses a heap to sort an array of elements. The heap property is maintained throughout the sorting process.

## Related Notes

- [[Priority Queue]]
- [[Heapsort]]

### Open Questions
What are some real-world applications of heaps in software engineering?

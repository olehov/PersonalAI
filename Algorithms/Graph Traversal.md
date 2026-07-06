# Graph Traversal

## Basics
Graph traversal is the process of visiting nodes and edges of a graph in a systematic way.

## Common Strategies

### Breadth-First Search
Breadth-first search explores nodes level by level from a starting point.

Typical use cases:

- shortest path in an unweighted graph
- connectivity checks
- level-order exploration

### Depth-First Search
Depth-first search explores as far as possible along a branch before backtracking.

Typical use cases:

- cycle detection
- topological ordering
- connected component discovery

## Complexity

- time: `O(V + E)`
- extra space: depends on traversal strategy and graph representation

## Why It Matters
Traversal is the foundation for many graph algorithms, including [[Dijkstra]] for weighted shortest paths.

## Related Notes

- [[Dijkstra]]
- [[Priority Queue]]

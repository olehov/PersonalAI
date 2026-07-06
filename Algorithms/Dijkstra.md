# Dijkstra

## Basics
Dijkstra's algorithm finds the shortest paths from a source node to all other reachable nodes in a graph with non-negative edge weights.

## Core Idea

1. Start from the source node with distance `0`.
2. Repeatedly pick the node with the currently smallest known distance.
3. Relax outgoing edges and update distances when a shorter path is found.

## Typical Implementation
A common implementation combines [[Graph Traversal]] ideas with a [[Priority Queue]] backed by a [[Heap]].

## Constraints

- edge weights must be non-negative
- not suitable for graphs with negative-weight edges

## Complexity

- with a binary [[Heap]] priority queue: `O((V + E) log V)`

## Related Notes

- [[Graph Traversal]]
- [[Priority Queue]]
- [[Heap]]

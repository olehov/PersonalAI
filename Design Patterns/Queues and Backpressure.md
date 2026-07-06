# Queues and Backpressure

## Basics
Queues decouple producers from consumers, while backpressure limits incoming work when downstream capacity is constrained.

## Why They Matter

- absorb bursts of traffic
- smooth uneven workloads
- protect slow consumers
- prevent system collapse under overload

## Common Patterns

- in-memory work queues
- message brokers
- bounded queues with rejection or throttling
- rate limiting paired with retry logic

## Algorithmic Connection
Priority-based scheduling may rely on a [[Priority Queue]], and some queue-processing systems use [[Heap]]-like structures for ordering.

## Systems Connection

- network-facing services may need backpressure in front of [[HTTP]] handlers
- slow upstream or downstream connections are influenced by [[TCP and UDP]] behavior
- operational diagnosis often depends on [[Observability]]
- retries without backpressure can worsen incidents, which links directly to [[Retries and Timeouts]]

## Related Notes

- [[Priority Queue]]
- [[Heap]]
- [[HTTP]]
- [[TCP and UDP]]
- [[Observability]]
- [[Retries and Timeouts]]

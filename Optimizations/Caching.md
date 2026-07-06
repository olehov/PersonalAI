# Caching

## Basics
Caching stores previously computed or recently fetched data so future requests can be served faster and with less repeated work.

## Common Goals

- reduce latency
- reduce backend load
- improve throughput
- smooth traffic spikes

## Common Cache Layers

- application-level caches
- database query caches
- HTTP caches in clients, proxies, or CDNs

## Tradeoffs

- stale data
- invalidation complexity
- memory overhead
- uneven performance during cache misses

## Where It Connects

- [[HTTP]] caching headers influence web and API behavior
- [[Load Balancing]] changes how cache locality behaves across instances
- [[DNS]] caching affects name resolution latency
- [[Priority Queue]]-style work scheduling can appear in cache refresh pipelines

## Related Notes

- [[HTTP]]
- [[Load Balancing]]
- [[DNS]]
- [[Priority Queue]]

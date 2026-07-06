# Load Balancing

## Basics
Load balancing distributes traffic across multiple servers or service instances to improve availability, scalability, and fault tolerance.

## Common Goals

- avoid overloading a single backend
- improve response times under load
- provide redundancy when instances fail

## Common Strategies

- round robin
- least connections
- weighted balancing
- hash-based routing

## Practical Context
Load balancing is commonly used in front of [[HTTP]] services and often relies on healthy backend connectivity over [[TCP and UDP|TCP]].

## Related Considerations

- DNS-based balancing can complement or front simple load balancing setups, which connects this topic to [[DNS]]
- encrypted traffic often introduces certificate and termination concerns tied to [[TLS]]

## Related Notes

- [[HTTP]]
- [[DNS]]
- [[TLS]]
- [[Caching]]
- [[Observability]]
- [[Queues and Backpressure]]

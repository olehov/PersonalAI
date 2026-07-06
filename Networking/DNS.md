# DNS

## Basics
DNS, the Domain Name System, maps human-readable domain names to IP addresses and other records used by networked systems.

## Why It Exists
Applications work better with stable names such as `example.com`, while the network ultimately routes traffic using IP addresses.

## Common Record Types

- `A`: maps a name to an IPv4 address
- `AAAA`: maps a name to an IPv6 address
- `CNAME`: points one name to another name
- `MX`: mail routing information
- `TXT`: arbitrary text, often for verification or policy

## Transport
DNS commonly uses [[TCP and UDP]]:

- `UDP` is typical for low-latency request/response lookups
- `TCP` is used when responses are too large, for zone transfers, or when reliability matters

## Resolution Path

1. client stub resolver
2. recursive resolver
3. authoritative name server

## Practical Relationship to Applications
Most user-facing protocols such as [[HTTP]] depend on DNS resolution before a connection can be established to the remote service.

## Related Notes

- [[TCP and UDP]]
- [[HTTP]]
- [[Caching]]
- [[Observability]]

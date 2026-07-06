# Sockets

## Basics
A socket is a programming interface for sending and receiving data over a network.

## Common Socket Families

- `AF_INET` for IPv4
- `AF_INET6` for IPv6
- `AF_UNIX` for local inter-process communication

## Common Socket Types

- stream sockets, usually backed by [[TCP and UDP|TCP]]
- datagram sockets, usually backed by [[TCP and UDP|UDP]]

## Typical Workflow

1. create a socket
2. bind it to an address if acting as a server
3. listen and accept connections for stream servers
4. send and receive data
5. close the socket

## Why It Matters
Sockets are the low-level interface beneath higher-level protocols such as [[HTTP]] and many custom network services.

## Related Notes

- [[TCP and UDP]]
- [[HTTP]]

# TLS

## Basics
TLS, Transport Layer Security, provides encryption, integrity, and peer authentication for network communication.

## What TLS Adds

- confidentiality through encryption
- integrity checks for transmitted data
- certificate-based server authentication

## Common Use Cases

- HTTPS for secure web traffic over [[HTTP]]
- encrypted API communication
- secure database and service-to-service connections

## Relationship to Other Protocols
TLS usually runs on top of reliable transport such as [[TCP and UDP|TCP]] and is commonly layered under protocols like [[HTTP]].

## Common Operational Concerns

- certificate expiration
- hostname mismatch
- unsupported protocol or cipher versions

## Related Notes

- [[HTTP]]
- [[TCP and UDP]]

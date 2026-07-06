# Retries and Timeouts

## Basics
Retries and timeouts are resilience mechanisms used when remote work may fail, stall, or complete too slowly.

## Timeouts

- connection timeout limits how long setup may take
- read timeout limits how long a response may take
- process timeout limits how long a task may run

## Retries

- useful for transient failures
- dangerous when the failure is persistent
- should usually be bounded and paired with backoff

## Common Risks

- retry storms
- duplicated work
- hidden latency growth
- extra pressure on already unhealthy systems

## Where It Connects

- retries often happen around [[HTTP]] calls
- timeout behavior depends on transport characteristics in [[TCP and UDP]]
- debugging failed retries may involve [[Pipes and Redirection]] and [[SSH]]
- service restarts or failures may surface through [[Systemd]]

## Related Notes

- [[HTTP]]
- [[TCP and UDP]]
- [[SSH]]
- [[Pipes and Redirection]]
- [[Systemd]]

# HTTP

## Basics
HTTP is an application-layer protocol used for client-server communication on the web and in many APIs.

## Request Structure

- method
- path
- headers
- optional body

## Response Structure

- status code
- headers
- optional body

## Common Methods

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`

## Transport
HTTP typically runs on top of [[TCP and UDP|TCP]], because ordered and reliable byte streams are important for request and response delivery.

In production environments, HTTP is frequently secured with [[TLS]] and distributed across backends with [[Load Balancing]].

## Common Status Code Groups

- `2xx`: success
- `3xx`: redirection
- `4xx`: client error
- `5xx`: server error

## Related Notes

- [[TCP and UDP]]
- [[DNS]]
- [[Sockets]]
- [[TLS]]
- [[Load Balancing]]
- [[Caching]]
- [[Retries and Timeouts]]
- [[Queues and Backpressure]]
- [[Observability]]

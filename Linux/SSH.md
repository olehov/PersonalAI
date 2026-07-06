# SSH

## Basics
SSH, the Secure Shell protocol, provides encrypted remote login, command execution, and tunneling.

## Common Use Cases

- remote shell access
- secure file transfer with related tools such as `scp` and `sftp`
- port forwarding and tunneling
- remote administration of services managed by [[Systemd]]

## Common Commands

### Connect
`ssh user@host`

### Copy a File
`scp local.txt user@host:/tmp/local.txt`

### Port Forwarding
`ssh -L 8080:localhost:80 user@host`

## Operational Notes

- SSH sessions often interact with foreground and background processes, so it pairs naturally with [[Job Control]] and [[Processes and Signals]].
- command output is frequently combined with [[Pipes and Redirection]] for remote debugging workflows.

## Related Notes

- [[Job Control]]
- [[Processes and Signals]]
- [[Pipes and Redirection]]
- [[Retries and Timeouts]]

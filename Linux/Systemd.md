# Systemd

## Basics
`systemd` is the service manager and init system used by many modern Linux distributions.

## Responsibilities

- boot orchestration
- service lifecycle management
- dependency handling between units
- logging integration through `journald`

## Common Unit Types

- `service`
- `socket`
- `target`
- `timer`

## Common Commands

### `systemctl status <unit>`
Show service status, recent logs, and state.

### `systemctl start <unit>`
Start a service.

### `systemctl stop <unit>`
Stop a service.

### `systemctl enable <unit>`
Enable a unit at boot.

### `journalctl -u <unit>`
Inspect logs for a specific service.

## Why It Matters
`systemd` manages long-running processes, restarts failed services, and is closely related to [[Processes and Signals]] when diagnosing production behavior.

## Related Notes

- [[Processes and Signals]]
- [[File Permissions]]
- [[Pipes and Redirection]]
- [[SSH]]
- [[Observability]]

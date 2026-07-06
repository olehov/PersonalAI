# Processes and Signals
A process is a program that is being executed by the operating system. In Linux, processes can be either running in the foreground or background.

### Parent-Child Relationships

* A parent process creates one or more child processes.
* Child processes inherit parts of their parent's execution context such as environment variables and open file descriptors.
* A parent can exit before its children. In that case, the orphaned child is re-parented to a system process such as `init` or `systemd`.

### Foreground and Background Execution

* Foreground processes are attached to the current terminal session and receive terminal input directly.
* Background processes continue running without blocking the shell prompt.
* Common shell job-control commands are `jobs`, `bg`, and `fg`.
* See [[Job Control]] for the shell-facing workflow built on top of processes and signals.

### Signals

Signals are asynchronous notifications sent to a process to indicate a specific event has occurred. Signals can be sent from one process to another, or they can be generated internally by the system.

#### SIGTERM vs SIGKILL

* `SIGTERM`: Sent when a process is terminated. The process can still handle the signal and perform any necessary cleanup.
* `SIGKILL`: Immediately terminates the process without giving it a chance to clean up.

### Common Debugging Commands

* `ps`: Displays information about running processes, including process IDs and parent-child relationships.
* `top`: Displays system resource usage and running processes in real time.
* `kill`: Sends a signal to a process. The default signal is `SIGTERM`, but it can also send signals such as `SIGKILL`.
* `jobs`: Lists the background jobs that are currently running.

### Open Questions

None.

## Related Notes

- [[Job Control]]

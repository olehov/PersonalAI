# File Permissions

## Basics
Linux file permissions control who can read, write, or execute files and directories.

## Permission Classes

- user
- group
- others

## Basic Permission Bits

- `r`: read
- `w`: write
- `x`: execute

## Common Commands

### `ls -l`
Show file mode bits, ownership, and group information.

### `chmod`
Change file permission bits.

### `chown`
Change file owner and, optionally, group.

### `chgrp`
Change only the group owner.

## Practical Notes

- execute permission on a directory controls traversal
- write permission on a directory controls creating, deleting, or renaming entries inside it
- permission issues often appear while debugging processes started by other users or services such as [[Systemd]]

## Related Notes

- [[Processes and Signals]]
- [[Systemd]]

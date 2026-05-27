# Console User Grain (macOS)

## Overview

This custom SaltStack grain retrieves the currently logged in console user on macOS systems.

It is useful for identifying the active interactive user session on a machine, rather than service accounts or system processes.

This is especially valuable in macOS environments where:
- Multiple users may exist on a system
- Background automation runs as root
- You need to target the currently active user session

## What the Grain Provides

The grain returns a single key:

```
console_user: username
```

### Example Output

When a user is logged in:

```
console_user: matt
```

When no user is logged in or retrieval fails:

```
console_user: None
```

## How It Works

The grain runs the following macOS command:

```
/usr/bin/stat -f%Su /dev/console
```

### What this does

- `/dev/console` represents the active graphical login session  
- `stat -f%Su` extracts the username owning the console session
- The result is the currently logged in GUI user

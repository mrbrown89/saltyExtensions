# Console User Grain (macOS)

## Overview

This custom SaltStack grain retrieves the currently logged in console user and their UID on macOS systems.

It is useful for identifying the active interactive user session on a machine, rather than service accounts or system processes.

This is especially valuable in macOS environments where:
- Multiple users may exist on a system
- Background automation runs as root
- You need to target the currently active user session
- LaunchAgents require a GUI user UID for `launchctl` operations
- Homebrew commands must run as the logged-in user rather than root

## What the Grain Provides

The grain returns two keys:

```yaml
console_user: username
console_uid: uid
```

### Example Output

When a user is logged in:

```yaml
console_user: matt
console_uid: 501
```

When no user is logged in or retrieval fails:

```yaml
console_user: None
console_uid: None
```

## How It Works

The grain runs the following macOS command:

```bash
/usr/bin/stat -f%Su /dev/console
```

### What this does

- `/dev/console` represents the active graphical login session
- `stat -f%Su` extracts the username owning the console session
- The result is the currently logged in GUI user

Once the username has been retrieved, Python uses the standard `pwd` module to look up the corresponding UID:

```python
uid = pwd.getpwnam(user).pw_uid
```

This allows Salt states to access both the username and the numeric UID associated with the active console session.

## Example Usage

### Accessing the Username

```jinja
{% set console_user = grains['console_user'] %}
```

### Accessing the UID

```jinja
{% set console_uid = grains['console_uid'] %}
```

### LaunchAgent Example

```yaml
load_launchagent:
  cmd.run:
    - name: launchctl bootstrap gui/{{ grains['console_uid'] }} /Library/LaunchAgents/com.example.agent.plist
```

### Homebrew Example

```yaml
install_package:
  cmd.run:
    - name: /opt/homebrew/bin/brew install wget
    - runas: {{ grains['console_user'] }}
```

## Error Handling

If the grain cannot determine the console user or UID, it returns:

```yaml
console_user: None
console_uid: None
```

This prevents Salt from failing unexpectedly and allows states to handle missing user sessions gracefully.

## Typical Use Cases

- Running Homebrew commands as the logged in user
- Loading or unloading LaunchAgents
- Deploying user specific configuration files
- Targeting the active GUI session
- Triggering user facing notifications
- Managing applications that require a logged-in user context

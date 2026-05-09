# macSoftware Salt Module

## Overview
The `macSoftware` module is a custom Salt execution module for macOS that allows you to:

- Query installed applications
- Retrieve versions and bundle identifiers
- Inspect code signing (Team ID, authority, etc.)
- Integrate with Installomator to determine latest available versions
- Decide whether an application requires updating

---

## Usage

### List Installed Apps
```bash
sudo salt-call --local macSoftware.getInstalledApps name="Slack"
```

### Find by Bundle ID (recommended)
```bash
sudo salt-call --local macSoftware.getInstalledApps bundleId="com.tinyspeck.slackmacgap"
```

### Get Installed Version
```bash
sudo salt-call --local macSoftware.getInstalledVersion bundleId="com.tinyspeck.slackmacgap"
```

### Check if Version Installed
```bash
sudo salt-call --local macSoftware.isVersionInstalled bundleId="com.tinyspeck.slackmacgap" version="4.49.81"
```

### Get Code Signing Info
```bash
sudo salt-call --local macSoftware.getAppSignature bundleId="com.tinyspeck.slackmacgap"
```

---

## Installomator Integration

### Get Latest Version Info
```bash
sudo salt-call --local macSoftware.getInstallomatorInfo slack
```

### Check if Update is Needed
```bash
sudo salt-call --local macSoftware.installomatorUpdateNeeded slack bundleId="com.tinyspeck.slackmacgap"
```

---

## Example State Usage

```yaml
install_slack:
  cmd.run:
    - name: /opt/saltyMacs/bin/Installomator.sh slack BLOCKING_PROCESS_ACTION=ignore NOTIFY=silent
    - onlyif: >
        salt-call --local --out=json macSoftware.installomatorUpdateNeeded slack bundleId="com.tinyspeck.slackmacgap" | grep '"updateNeeded": true'
```

---

## Example Pillar

```yaml
managed_apps:
  slack:
    installomator_label: slack
    bundle_id: com.tinyspeck.slackmacgap
    installomator_args:
      - BLOCKING_PROCESS_ACTION=ignore
      - NOTIFY=silent
```

---

## View all Installed Software

Return a simplified inventory of installed macOS applications.

This function scans standard macOS application directories and returns
application metadata including name, version, bundle identifier, and optionally
installation paths.

The function supports both system-wide and per-user application discovery.

---

### Function

```python
listInstalledSoftware(
    includeVersions=True,
    includeBundleIds=True,
    includePaths=False,
    includeSystemApps=True,
    includeUserApplications=True,
    searchPaths=None,
    sort=True,
)
```

---

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `includeVersions` | `bool` | `True` | Include application version information |
| `includeBundleIds` | `bool` | `True` | Include bundle identifiers |
| `includePaths` | `bool` | `False` | Include full application paths |
| `includeSystemApps` | `bool` | `True` | Include Apple system applications |
| `includeUserApplications` | `bool` | `True` | Include applications from `/Users/*/Applications` |
| `searchPaths` | `list` | `None` | Custom application search paths |
| `sort` | `bool` | `True` | Sort results alphabetically |

---

### Example Usage

#### List all installed software

```bash
salt-call --local macSoftware.listInstalledSoftware
```

#### Include application paths

```bash
salt-call --local macSoftware.listInstalledSoftware includePaths=True
```

#### Exclude Apple system applications

```bash
salt-call --local macSoftware.listInstalledSoftware includeSystemApps=False
```

#### Search custom locations only

```bash
salt-call --local macSoftware.listInstalledSoftware searchPaths='["/Applications/Utilities"]'
```

---

### Example Output

```yaml
local:
  - name: Google Chrome
    version: 137.0.7151.69
    bundleId: com.google.Chrome

  - name: Slack
    version: 4.43.51
    bundleId: com.tinyspeck.slackmacgap

  - name: Visual Studio Code
    version: 1.101.0
    bundleId: com.microsoft.VSCode
```

---

## Notes

- Applications are discovered by recursively scanning `.app` bundles.
- Metadata is read directly from each application's `Info.plist`.
- This function does not perform code-signing or Gatekeeper checks.
- Duplicate application paths are automatically filtered.
- Results are intended for inventory, compliance, and software auditing workflows.


---

## Design Notes

- Prefer **bundleId** over app name
- `updateNeeded: true` → run Installomator
- If latest version can't be determined → update by default (safe fallback)

---

## Summary

This module provides a clean separation:

- Salt module → detection
- Installomator → installation
- Salt states → enforcement

Result: faster, cleaner macOS management.

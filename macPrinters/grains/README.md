# Mac Printers

## Overview

This custom grain for SaltStack collects information about configured printers on macOS systems.

It exposes:
- A list of installed printers  
- A count of configured printers  

This is useful for auditing, compliance checks, and conditional state execution.

## What the Grain Provides

The grain returns two values:

```
macos_printers:
  - Printer1
  - Printer2

macos_printer_count: 2
```

## How It Works

The grain runs:

```
lpstat -p
```

It parses output lines beginning with:

```
printer <name>
```

If the command fails, it safely returns:

```
macos_printers: []
macos_printer_count: 0
```

## Example Usage

### List printers on macOS minions

```
salt 'os:MacOS' grains.get macos_printers
```

### Get printer count

```
salt '*' grains.get macos_printer_count
```

### Target machines with printers

```
salt -G 'macos_printer_count:>0' test.ping
```

### Target machines without printers

```
salt -G 'macos_printer_count:0' test.ping
```

## Real-World Use Cases

- Audit printer presence across endpoints  
- Detect unauthorised printer additions  
- Apply configuration conditionally  
- Use with MDM to trigger custom work flows

---

## Notes

- macOS only (uses `/usr/bin/lpstat`)  
- Requires CUPS  
- Output depends on system configuration

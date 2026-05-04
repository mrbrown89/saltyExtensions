import subprocess

def macos_printers():
    grains = {}

    try:
        result = subprocess.run(
            ["/usr/bin/lpstat", "-p"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

        printers = []
        for line in result.stdout.splitlines():
            if line.startswith("printer "):
                printers.append(line.split()[1])

        grains["macos_printers"] = printers
        grains["macos_printer_count"] = len(printers)

    except Exception:
        grains["macos_printers"] = []
        grains["macos_printer_count"] = 0

    return grains

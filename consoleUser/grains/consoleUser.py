import subprocess


def console_user():
    """
    Return the currently logged in console user on macOS.
    """

    try:
        user = subprocess.check_output(
            ["/usr/bin/stat", "-f%Su", "/dev/console"],
            text=True
        ).strip()

        return {
            "console_user": user
        }

    except Exception:
        return {
            "console_user": None
        }

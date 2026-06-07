import subprocess
import pwd


def console_user():
    """
    Return the currently logged in console user and UID on macOS.
    """

    try:
        user = subprocess.check_output(
            ["/usr/bin/stat", "-f%Su", "/dev/console"],
            text=True
        ).strip()

        uid = pwd.getpwnam(user).pw_uid

        return {
            "console_user": user,
            "console_uid": uid
        }

    except Exception:
        return {
            "console_user": None,
            "console_uid": None
        }


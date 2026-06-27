"""
Salt state module for managing Workbrew packages on macOS.

Example usage:

brew_formulae:
  workbrew.installed:
    - pkgs:
      - nmap
      - mactop

brew_casks:
  workbrew.installed:
    - pkgs:
      - cyberduck

hashicorp_packages:
  workbrew.installed:
    - pkgs:
      - hashicorp/tap/terraform
      - hashicorp/tap/packer
"""

from __future__ import absolute_import, print_function, unicode_literals

from salt.exceptions import CommandExecutionError

__virtualname__ = "workbrew"


def __virtual__():
    """
    Load only when the Workbrew execution module is available.
    """
    if "workbrew.install" not in __salt__:
        return False, "workbrew execution module not loaded"

    return __virtualname__


def installed(name, pkgs=None):
    """
    Ensure one or more Workbrew packages are installed.
    """
    targets = pkgs or [name]

    changes = {}
    comments = []
    result = True

    for pkg in targets:
        if __salt__["workbrew.is_installed"](pkg):
            comments.append("Package {} is already installed".format(pkg))
            continue

        if __opts__.get("test", False):
            result = None
            changes[pkg] = {"old": None, "new": "installed"}
            comments.append("Package {} would be installed".format(pkg))
            continue

        try:
            ret = __salt__["workbrew.install"](pkg)
            status = ret.get("status")

            if status == "installed":
                changes[pkg] = {"old": None, "new": "installed"}
                comments.append("Installed package {}".format(pkg))

            elif status == "already_installed":
                comments.append("Package {} is already installed".format(pkg))

            elif status == "app_present_unmanaged":
                result = False
                comments.append(
                    ret.get(
                        "comment",
                        (
                            "Application for package {} already exists in "
                            "/Applications but is not managed by Workbrew"
                        ).format(pkg),
                    )
                )

            else:
                if ret.get("result", False):
                    comments.append("No changes needed for package {}".format(pkg))
                else:
                    result = False
                    comments.append(
                        ret.get("comment", "Failed to install package {}".format(pkg))
                    )

        except CommandExecutionError as exc:
            result = False
            comments.append("Failed to install package {}: {}".format(pkg, exc))

    return {
        "name": name,
        "result": result,
        "changes": changes,
        "comment": "\n".join(comments),
    }


def removed(name, pkgs=None):
    """
    Ensure one or more Workbrew packages are removed.
    """
    targets = pkgs or [name]

    changes = {}
    comments = []
    result = True

    for pkg in targets:
        if not __salt__["workbrew.is_installed"](pkg):
            comments.append("Package {} is already absent".format(pkg))
            continue

        if __opts__.get("test", False):
            result = None
            changes[pkg] = {"old": "installed", "new": None}
            comments.append("Package {} would be removed".format(pkg))
            continue

        try:
            ret = __salt__["workbrew.remove"](pkg)
            status = ret.get("status")

            if status == "removed":
                changes[pkg] = {"old": "installed", "new": None}
                comments.append("Removed package {}".format(pkg))

            elif status == "already_absent":
                comments.append("Package {} is already absent".format(pkg))

            else:
                if ret.get("result", False):
                    comments.append("No changes needed for package {}".format(pkg))
                else:
                    result = False
                    comments.append(
                        ret.get("comment", "Failed to remove package {}".format(pkg))
                    )

        except CommandExecutionError as exc:
            result = False
            comments.append("Failed to remove package {}: {}".format(pkg, exc))

    return {
        "name": name,
        "result": result,
        "changes": changes,
        "comment": "\n".join(comments),
    }

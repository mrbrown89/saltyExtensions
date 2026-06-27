"""
Salt execution module for managing Workbrew packages on macOS.

This module uses the Workbrew brew binary:

    /opt/workbrew/bin/brew

Salt only ensures packages are present or absent.

Updates and upgrades are intentionally handled elsewhere by the Workbrew
update/upgrade LaunchDaemon.
"""

from __future__ import absolute_import, print_function, unicode_literals

import json
import os

from salt.exceptions import CommandExecutionError

__virtualname__ = "workbrew"

BREW_BIN = "/opt/workbrew/bin/brew"


def __virtual__():
    """
    Load only on macOS systems where the Workbrew brew binary exists.
    """
    if __grains__.get("os") != "MacOS":
        return False, "workbrew execution module only works on macOS"

    if not os.path.exists(BREW_BIN):
        return False, "Workbrew binary not found at {}".format(BREW_BIN)

    return __virtualname__


def _run(args, failhard=True):
    """
    Run the Workbrew brew binary with update/upgrade behaviour disabled.
    """
    cmd = [BREW_BIN] + args

    env = {
        "HOMEBREW_NO_AUTO_UPDATE": "1",
        "HOMEBREW_NO_ENV_HINTS": "1",
        "HOMEBREW_NO_INSTALL_UPGRADE": "1",
    }

    ret = __salt__["cmd.run_all"](
        cmd,
        python_shell=False,
        env=env,
        ignore_retcode=True,
        output_loglevel="quiet",
    )

    if failhard and ret.get("retcode", 1) != 0:
        raise CommandExecutionError(
            ret.get("stderr") or ret.get("stdout") or "brew command failed",
            info=ret,
        )

    return ret


def _short_name(name):
    """
    Return package name without tap qualification.
    """
    return name.split("/")[-1]


def _brew_prefix():
    """
    Return the actual Workbrew prefix reported by brew.
    """
    ret = _run(["--prefix"], failhard=False)

    if ret.get("retcode", 1) != 0:
        return "/opt/homebrew"

    return ret.get("stdout", "").strip() or "/opt/homebrew"


def _info(name):
    """
    Return parsed ``brew info --json=v2 <name>`` data.

    Results are cached in ``__context__`` to avoid repeated brew calls during
    a single Salt run.
    """
    cache = __context__.setdefault("workbrew.info", {})

    if name in cache:
        return cache[name]

    ret = _run(["info", "--json=v2", name], failhard=False)

    if ret.get("retcode", 1) != 0 or not ret.get("stdout"):
        cache[name] = {}
        return cache[name]

    try:
        cache[name] = json.loads(ret["stdout"])
    except ValueError:
        cache[name] = {}

    return cache[name]


def _classify(name):
    """
    Classify a package as ``formula`` or ``cask``.

    Fully-qualified tapped packages are treated as formulae in this initial
    implementation. Otherwise, brew info JSON is inspected. If classification
    is uncertain, the package defaults to ``formula``.
    """
    if name.count("/") >= 2:
        return "formula"

    data = _info(name)
    formulae = data.get("formulae", []) or []
    casks = data.get("casks", []) or []

    if casks and not formulae:
        return "cask"

    if formulae and not casks:
        return "formula"

    return "formula"


def _cask_artifact_apps(name):
    """
    Extract .app artifact names for a cask from brew info JSON.
    """
    data = _info(name)
    apps = []

    for cask in data.get("casks", []) or []:
        artifacts = cask.get("artifacts", []) or []

        for artifact in artifacts:
            if isinstance(artifact, list):
                for item in artifact:
                    if isinstance(item, str) and item.endswith(".app"):
                        apps.append(item)

            elif isinstance(artifact, dict):
                app_artifact = artifact.get("app")

                if isinstance(app_artifact, str) and app_artifact.endswith(".app"):
                    apps.append(app_artifact)

                elif isinstance(app_artifact, list):
                    for item in app_artifact:
                        if isinstance(item, str) and item.endswith(".app"):
                            apps.append(item)

    return sorted(set(apps))


def _cask_app_paths(name):
    """
    Return likely /Applications paths for a cask.
    """
    return [os.path.join("/Applications", app) for app in _cask_artifact_apps(name)]


def cask_app_present(name):
    """
    Return True if a cask's app bundle already exists in /Applications.
    """
    for path in _cask_app_paths(name):
        if os.path.exists(path):
            return True

    return False


def list_pkgs():
    """
    Return installed Workbrew packages as a dict of name -> version.

    Uses:

        brew list --versions

    The result is cached in ``__context__`` for the duration of the Salt run.

    If brew list fails, this function raises CommandExecutionError. Returning
    an empty dict on failure would be unsafe because the state layer would
    treat every package as absent.
    """
    if "workbrew.list_pkgs" in __context__:
        return __context__["workbrew.list_pkgs"]

    ret = _run(["list", "--versions"], failhard=False)

    if ret.get("retcode", 1) != 0:
        raise CommandExecutionError(
            ret.get("stderr") or ret.get("stdout") or "brew list --versions failed",
            info=ret,
        )

    pkgs = {}

    for line in ret.get("stdout", "").splitlines():
        parts = line.split()

        if len(parts) >= 2:
            pkgs[parts[0]] = " ".join(parts[1:])

    __context__["workbrew.list_pkgs"] = pkgs
    return pkgs


def _clear_pkg_cache():
    """
    Clear cached package data after install or removal.
    """
    __context__.pop("workbrew.list_pkgs", None)


def version(name):
    """
    Return the installed version string for a package, or an empty string.
    """
    pkgs = list_pkgs()
    short_name = _short_name(name)

    return pkgs.get(name, "") or pkgs.get(short_name, "")


def is_installed(name):
    """
    Return True if Workbrew reports the package as installed.

    This checks the full installed package list because Workbrew may report
    tapped formulae by short name, for example:

        terraform 1.15.4
    """
    pkgs = list_pkgs()
    short_name = _short_name(name)

    return name in pkgs or short_name in pkgs


def install(name):
    """
    Install a Workbrew formula or cask if it is not already installed.

    This function does not update Homebrew metadata and does not upgrade
    existing packages. Updates and upgrades are handled outside Salt by the
    Workbrew LaunchDaemon.

    Returns a dictionary containing a result, status, and optional version or
    comment.
    """
    if is_installed(name):
        return {
            "result": True,
            "status": "already_installed",
            "version": version(name),
        }

    kind = _classify(name)

    if kind == "cask":
        if cask_app_present(name):
            return {
                "result": False,
                "status": "app_present_unmanaged",
                "comment": (
                    "Application already exists in /Applications but is not "
                    "managed by Workbrew"
                ),
            }

        _run(["install", "--cask", name])
        _clear_pkg_cache()

        return {
            "result": True,
            "status": "installed",
            "version": version(name),
        }

    _run(["install", name])
    _clear_pkg_cache()

    return {
        "result": True,
        "status": "installed",
        "version": version(name),
    }


def remove(name):
    """
    Remove a Workbrew formula or cask if it is installed.
    """
    if not is_installed(name):
        return {
            "result": True,
            "status": "already_absent",
        }

    kind = _classify(name)

    if kind == "cask":
        _run(["uninstall", "--cask", name])
    else:
        _run(["uninstall", name])

    _clear_pkg_cache()

    return {
        "result": True,
        "status": "removed",
    }


def brew_prefix():
    """
    Return the Workbrew prefix.

    This is primarily useful for debugging.
    """
    return _brew_prefix()


def caskroom_path():
    """
    Return the Workbrew Caskroom path.

    This is primarily useful for debugging.
    """
    return os.path.join(_brew_prefix(), "Caskroom")

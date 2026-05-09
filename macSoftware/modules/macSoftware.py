import os
import plistlib
import subprocess

import salt.utils.platform


def __virtual__():
    if salt.utils.platform.is_darwin():
        return "macSoftware"
    return (False, "The macSoftware module only works on macOS")


def _run(cmd):
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except Exception:
        return "", "", 1


def _readPlist(appPath):
    plistPath = os.path.join(appPath, "Contents", "Info.plist")

    if not os.path.exists(plistPath):
        return {}

    try:
        with open(plistPath, "rb") as plistFile:
            return plistlib.load(plistFile)
    except Exception:
        return {}


def _getSignatureInfo(appPath):
    stdout, stderr, retcode = _run(
        ["/usr/bin/codesign", "-dv", "--verbose=4", appPath]
    )

    output = "\n".join([stdout, stderr])

    info = {
        "signed": retcode == 0,
        "teamId": None,
        "authority": [],
        "identifier": None,
    }

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("TeamIdentifier="):
            info["teamId"] = line.split("=", 1)[1]

        elif line.startswith("Authority="):
            info["authority"].append(line.split("=", 1)[1])

        elif line.startswith("Identifier="):
            info["identifier"] = line.split("=", 1)[1]

    info["raw"] = output
    return info


def _getSpctlInfo(appPath):
    stdout, stderr, retcode = _run(
        ["/usr/sbin/spctl", "--assess", "--type", "execute", "--verbose=4", appPath]
    )

    output = "\n".join([stdout, stderr])

    return {
        "accepted": retcode == 0,
        "assessment": output,
    }


def _iterAppBundles(searchPaths=None, includeUserApplications=True):
    if searchPaths is None:
        searchPaths = [
            "/Applications",
            "/System/Applications",
            "/System/Applications/Utilities",
        ]

        if includeUserApplications:
            usersPath = "/Users"
            if os.path.exists(usersPath):
                for username in os.listdir(usersPath):
                    userApps = os.path.join(usersPath, username, "Applications")
                    if os.path.isdir(userApps):
                        searchPaths.append(userApps)

    seen = set()

    for rootPath in searchPaths:
        if not os.path.isdir(rootPath):
            continue

        for root, dirs, files in os.walk(rootPath):
            for dirname in list(dirs):
                if dirname.endswith(".app"):
                    appPath = os.path.join(root, dirname)

                    if appPath not in seen:
                        seen.add(appPath)
                        yield appPath

                    dirs.remove(dirname)


def _matches(value, pattern, exact=False):
    if value is None or pattern is None:
        return False

    valueLower = str(value).strip().lower()
    patternLower = str(pattern).strip().lower()

    if exact:
        return valueLower == patternLower

    return patternLower in valueLower


def _versionKey(version):
    if version is None:
        return ()

    parts = []

    for part in str(version).replace("-", ".").split("."):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part.lower())

    return tuple(parts)


def getInstalledApps(
    name=None,
    exact=False,
    bundleId=None,
    teamId=None,
    includeSignature=True,
    includeGatekeeper=False,
    includeUserApplications=True,
    searchPaths=None,
):
    matches = []

    for appPath in _iterAppBundles(
        searchPaths=searchPaths,
        includeUserApplications=includeUserApplications,
    ):
        plist = _readPlist(appPath)

        displayName = (
            plist.get("CFBundleDisplayName")
            or plist.get("CFBundleName")
            or os.path.basename(appPath).replace(".app", "")
        )

        bundleIdentifier = plist.get("CFBundleIdentifier")
        shortVersion = plist.get("CFBundleShortVersionString")
        buildVersion = plist.get("CFBundleVersion")

        if name and not _matches(displayName, name, exact=exact):
            continue

        if bundleId and not _matches(bundleIdentifier, bundleId, exact=exact):
            continue

        signatureInfo = None

        if includeSignature or teamId:
            signatureInfo = _getSignatureInfo(appPath)

        if teamId:
            foundTeamId = signatureInfo.get("teamId") if signatureInfo else None
            if not _matches(foundTeamId, teamId, exact=exact):
                continue

        appInfo = {
            "displayName": displayName,
            "path": appPath,
            "bundleId": bundleIdentifier,
            "displayVersion": shortVersion,
            "buildVersion": buildVersion,
            "minimumSystemVersion": plist.get("LSMinimumSystemVersion"),
            "bundleExecutable": plist.get("CFBundleExecutable"),
            "bundlePackageType": plist.get("CFBundlePackageType"),
            "copyright": plist.get("NSHumanReadableCopyright"),
        }

        if signatureInfo:
            appInfo["signature"] = signatureInfo

        if includeGatekeeper:
            appInfo["gatekeeper"] = _getSpctlInfo(appPath)

        matches.append(appInfo)

    return matches


def getInstalledVersion(
    name=None,
    exact=False,
    bundleId=None,
    teamId=None,
    searchPaths=None,
):
    matches = getInstalledApps(
        name=name,
        exact=exact,
        bundleId=bundleId,
        teamId=teamId,
        includeSignature=bool(teamId),
        searchPaths=searchPaths,
    )

    if not matches:
        return None

    versionedMatches = [m for m in matches if m.get("displayVersion")]

    if not versionedMatches:
        return None

    bestMatch = sorted(
        versionedMatches,
        key=lambda m: _versionKey(m.get("displayVersion")),
        reverse=True,
    )[0]

    return bestMatch.get("displayVersion")


def isVersionInstalled(
    name=None,
    version=None,
    exact=False,
    bundleId=None,
    teamId=None,
    searchPaths=None,
):
    if version is None:
        return False

    installedVersion = getInstalledVersion(
        name=name,
        exact=exact,
        bundleId=bundleId,
        teamId=teamId,
        searchPaths=searchPaths,
    )

    if installedVersion is None:
        return False

    return str(installedVersion).strip() == str(version).strip()


def getAppSignature(name=None, exact=False, bundleId=None, path=None, searchPaths=None):
    if path:
        if os.path.isdir(path):
            return _getSignatureInfo(path)
        return None

    matches = getInstalledApps(
        name=name,
        exact=exact,
        bundleId=bundleId,
        includeSignature=True,
        searchPaths=searchPaths,
    )

    if not matches:
        return None

    return matches[0].get("signature")


def getAppByBundleId(bundleId, searchPaths=None):
    return getInstalledApps(bundleId=bundleId, exact=True, searchPaths=searchPaths)


def getInstallomatorInfo(
    label,
    installomatorPath="/opt/saltyMacs/bin/Installomator.sh",
    debugLevel="2",
):
    """
    Run Installomator in debug mode and return parsed metadata.

    CLI Examples:
        salt-call --local macSoftware.getInstallomatorInfo slack
        salt-call --local macSoftware.getInstallomatorInfo jamfcheck
    """
    stdout, stderr, retcode = _run(
        [
            installomatorPath,
            label,
            "DEBUG={0}".format(debugLevel),
            "NOTIFY=silent",
            "BLOCKING_PROCESS_ACTION=ignore",
        ]
    )

    output = "\n".join([stdout, stderr])

    info = {
        "label": label,
        "retcode": retcode,
        "latestVersion": None,
        "downloadUrl": None,
        "name": None,
        "raw": output,
    }

    for line in output.splitlines():
        cleanLine = line.strip()

        if "appNewVersion" in cleanLine:
            info["latestVersion"] = cleanLine.split(":", 1)[-1].strip()

        elif "Latest version of" in cleanLine and " is " in cleanLine:
            info["latestVersion"] = cleanLine.rsplit(" is ", 1)[-1].strip()

        elif "downloadURL" in cleanLine:
            info["downloadUrl"] = cleanLine.split(":", 1)[-1].strip()

        elif cleanLine.startswith("name="):
            info["name"] = cleanLine.split("=", 1)[1].strip()

    return info

def installomatorUpdateNeeded(
    label,
    name=None,
    bundleId=None,
    exact=False,
    installomatorPath="/opt/saltyMacs/bin/Installomator.sh",
    searchPaths=None,
):
    installedVersion = getInstalledVersion(
        name=name,
        exact=exact,
        bundleId=bundleId,
        searchPaths=searchPaths,
    )

    installomatorInfo = getInstallomatorInfo(
        label=label,
        installomatorPath=installomatorPath,
    )

    latestVersion = installomatorInfo.get("latestVersion")

    result = {
        "label": label,
        "name": name,
        "bundleId": bundleId,
        "searchPaths": searchPaths,
        "installedVersion": installedVersion,
        "latestVersion": latestVersion,
        "updateNeeded": False,
        "reason": None,
    }

    if installedVersion is None:
        result["updateNeeded"] = True
        result["reason"] = "App is not installed"
        return result

    if latestVersion is None:
        result["updateNeeded"] = True
        result["reason"] = "Installomator latest version could not be determined"
        return result

    if str(installedVersion).strip() != str(latestVersion).strip():
        result["updateNeeded"] = True
        result["reason"] = "Installed version differs from latest version"
        return result

    result["reason"] = "Installed version matches latest version"
    return result

def listInstalledSoftware(
    includeVersions=True,
    includeBundleIds=True,
    includePaths=False,
    includeSystemApps=True,
    includeUserApplications=True,
    searchPaths=None,
    sort=True,
):

    """
    Return a simplified inventory of installed macOS applications.
    CLI Examples:
        salt-call --local macSoftware.listInstalledSoftware
        salt-call --local macSoftware.listInstalledSoftware includePaths=True
        salt-call --local macSoftware.listInstalledSoftware includeSystemApps=False
    """

    if searchPaths is None:
        searchPaths = []
        searchPaths.append("/Applications")

        if includeSystemApps:
            searchPaths.extend(
                [
                    "/System/Applications",
                    "/System/Applications/Utilities",
                ]
            )

    apps = getInstalledApps(
        includeSignature=False,
        includeGatekeeper=False,
        includeUserApplications=includeUserApplications,
        searchPaths=searchPaths,
    )

    results = []

    for app in apps:
        item = {
            "name": app.get("displayName"),
        }

        if includeVersions:
            item["version"] = app.get("displayVersion")
        
        if includeBundleIds:
            item["bundleId"] = app.get("bundleId")

        if includePaths:
            item["path"] = app.get("path")
        results.append(item)

    if sort:
        results = sorted(
            results,
            key=lambda x: (x.get("name") or "").lower(),
        )

    return results

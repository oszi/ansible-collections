# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring,line-too-long
import re

from typing import Dict, Iterable

# tld.domain.App[.Component][/arch][/version]
FLATPAK_APP_RE = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*(?:[./][a-zA-Z0-9][a-zA-Z0-9_-]*)+$")

# App identifier tail components to turn into alias suffixes
FLATPAK_APP_TAIL_COMPONENTS = frozenset(
    {
        "app",
        "application",
        "beta",
        "canary",
        "cli",
        "client",
        "codecs",
        "community",
        "communityedition",
        "compat",
        "default",
        "desktop",
        "desktopclient",
        "dev",
        "devel",
        "development",
        "edge",
        "extra",
        "free",
        "freeedition",
        "gl",
        "gl32",
        "gtk",
        "gui",
        "i386",
        "insiders",
        "linux",
        "nightly",
        "personal",
        "platform",
        "preview",
        "qt",
        "snapshot",
        "stable",
        "unstable",
    }
)


def flatpak_app_auto_alias(flatpak_app: str) -> str:
    if not isinstance(flatpak_app, str) or FLATPAK_APP_RE.match(flatpak_app) is None:
        raise ValueError(f"flatpak_app_auto_alias: 'flatpak_app' {flatpak_app!r} is not a valid app identifier")

    # Split /arch/version first, normalize components, drop the tld
    components = flatpak_app.split("/")[0].lower().replace("-", ".").split(".")[1:]

    i = len(components) - 1
    while i >= 0 and components[i] in FLATPAK_APP_TAIL_COMPONENTS:
        i -= 1

    if i < 0:
        raise ValueError(f"flatpak_app_auto_alias: all components ignored in 'flatpak_app' {flatpak_app!r}")

    return "-".join(components[i:])


def flatpak_apps_to_auto_aliases(flatpak_apps: Iterable[str]) -> Dict[str, str]:
    if isinstance(flatpak_apps, (str, bytes)):
        raise ValueError("flatpak_apps_to_auto_aliases: 'flatpak_apps' must be an iterable of app identifiers")

    result = {flatpak_app_auto_alias(app): f"flatpak run {app}" for app in flatpak_apps}
    return result


# pylint: disable=too-few-public-methods
class FilterModule:
    def filters(self):
        return {
            "flatpak_app_auto_alias": flatpak_app_auto_alias,
            "flatpak_apps_to_auto_aliases": flatpak_apps_to_auto_aliases,
        }

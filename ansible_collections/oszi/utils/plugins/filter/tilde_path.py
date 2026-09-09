# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring,line-too-long
import re
import shlex

# Do not use path functions that use the filesystem, filters run on the ansible controller.
from posixpath import isabs, normpath, sep as SEP

TILDE = "~"

USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

HOME_VAR_RE = re.compile(r"^(\$HOME\b|\$\{HOME\})")

HOME_VAR_QUOTED_RE = re.compile(r'^"(\$HOME\b|\$\{HOME\})([^"\\]*)"')


def to_tilde_path(path: str, home: str, user: str = "") -> str:
    if not isinstance(path, str) or not isabs(path):
        raise ValueError("to_tilde_path: 'path' is not an absolute path string")
    if not isinstance(home, str) or not isabs(home):
        raise ValueError("to_tilde_path: 'home' is not an absolute path string")
    if not isinstance(user, str) or (user and USERNAME_RE.fullmatch(user) is None):
        raise ValueError("to_tilde_path: 'user' is not a valid username string")

    path_norm = normpath(path)
    home_norm = normpath(home)

    if path_norm.startswith(home_norm):
        relpath = path_norm[len(home_norm) :]
        if relpath == "" or relpath.startswith(SEP):
            trail_sep = SEP if path.endswith(SEP) else ""
            return TILDE + user + relpath + trail_sep

    return path  # Change nothing.


def home_var_to_tilde_path(path: str, user: str = "") -> str:
    if not isinstance(path, str):
        raise ValueError("home_var_to_tilde_path: 'path' is not a string")
    if not isinstance(user, str) or (user and USERNAME_RE.fullmatch(user) is None):
        raise ValueError("home_var_to_tilde_path: 'user' is not a valid username string")

    relpath = None
    if (path_match := HOME_VAR_RE.match(path)) is not None:
        relpath = path[path_match.end() :]
    elif (path_match := HOME_VAR_QUOTED_RE.match(path)) is not None:
        relpath = path_match.group(2) + path[path_match.end() :]

    if relpath is not None and (relpath == "" or relpath.startswith(SEP)):
        return TILDE + user + relpath

    return path  # Change nothing.


def quote_tilde_path(path: str) -> str:
    if not isinstance(path, str):
        raise ValueError("quote_tilde_path: 'path' is not a string")

    if not path.startswith(TILDE):
        return shlex.quote(path)

    basepath, sep, relpath = path.partition(SEP)

    if basepath != TILDE:
        basepath = TILDE + shlex.quote(basepath[len(TILDE) :])

    if relpath != "":
        relpath = shlex.quote(relpath)

    return basepath + sep + relpath


def to_quoted_tilde_path(path: str, home: str, user: str = "") -> str:
    tilde_path = to_tilde_path(path, home, user)
    return quote_tilde_path(tilde_path)


def home_var_to_quoted_tilde_path(path: str, user: str = "") -> str:
    tilde_path = home_var_to_tilde_path(path, user)
    return quote_tilde_path(tilde_path)


# pylint: disable=too-few-public-methods
class FilterModule:
    def filters(self):
        return {
            "to_tilde_path": to_tilde_path,
            "to_quoted_tilde_path": to_quoted_tilde_path,
            "home_var_to_tilde_path": home_var_to_tilde_path,
            "home_var_to_quoted_tilde_path": home_var_to_quoted_tilde_path,
            "quote_tilde_path": quote_tilde_path,
        }

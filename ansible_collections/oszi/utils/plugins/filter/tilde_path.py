# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring,line-too-long
import re
import shlex

# Do not use path functions that use the filesystem, filters run on the ansible controller.
from posixpath import isabs, normpath, sep

USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def to_tilde_path(path: str, home: str, user: str = "") -> str:
    if not isinstance(path, str) or not isabs(path):
        raise ValueError("to_tilde_path: 'path' is not an absolute path string")
    if not isinstance(home, str) or not isabs(home):
        raise ValueError("to_tilde_path: 'home' is not an absolute path string")
    if not isinstance(user, str) or (user and USERNAME_RE.match(user) is None):
        raise ValueError("to_tilde_path: 'user' is not a valid username string")

    path_norm = normpath(path)
    home_norm = normpath(home)

    if path_norm.startswith(home_norm):
        relpath = path_norm[len(home_norm) :]
        if relpath == "" or relpath.startswith(sep):
            trail_sep = sep if path.endswith(sep) else ""
            return f"~{user}" + relpath + trail_sep

    return path  # Change nothing.


def quote_tilde_path(path: str) -> str:
    if not isinstance(path, str):
        raise ValueError("quote_tilde_path: 'path' is not a string")

    if not path.startswith("~"):
        return shlex.quote(path)

    basepath, sep_, relpath = path.partition(sep)
    if not relpath:
        return basepath + sep_

    return basepath + sep_ + shlex.quote(relpath)


def to_quoted_tilde_path(path: str, home: str, user: str = "") -> str:
    tilde_path = to_tilde_path(path, home, user)
    return quote_tilde_path(tilde_path)


# pylint: disable=too-few-public-methods
class FilterModule:
    def filters(self):
        return {
            "to_tilde_path": to_tilde_path,
            "to_quoted_tilde_path": to_quoted_tilde_path,
            "quote_tilde_path": quote_tilde_path,
        }

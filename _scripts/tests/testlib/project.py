# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import re
import shlex

from pathlib import Path
from typing import Iterable, List, NoReturn, Optional

from .runner import error_code, run_shell_get_lines

__all__ = [
    "RELEASE_TAG_GLOB",
    "SCRIPT_PATHSPECS",
    "PYTHON_INTERPRETERS",
    "PYTHON_PATHSPECS",
    "SHELL_INTERPRETERS",
    "SHELL_PATHSPECS",
    "chdir_project",
    "git_latest_release_tag",
    "git_previous_release_tag",
    "git_changed_paths",
    "git_ls_files",
    "git_ls_files_with_interpreters",
    "has_shebang",
]

RELEASE_TAG_GLOB = "[0-9]*.[0-9]*.[0-9]*"

# Executable scripts without a file extension, identified by their shebang.
SCRIPT_PATHSPECS = ("**scripts/*", "**/bin/*", "**/sbin/*", ":!:*.j2", ":!:*.jinja2", ":!:*.jinja")

PYTHON_INTERPRETERS = ("python", "python3")
PYTHON_PATHSPECS = ("*.py",)

SHELL_INTERPRETERS = ("sh", "bash", "ksh", "zsh")
SHELL_PATHSPECS = (*(f"*.{i}" for i in SHELL_INTERPRETERS), "**/*shrc", "**/.*profile")


def chdir_project(paths: Iterable[str] = ()) -> List[str] | NoReturn:
    """Change to the project directory like run-tests.sh, and rebase paths relative to the original directory."""
    cwd = os.getcwd()
    project = Path(run_shell_get_lines("git rev-parse --show-toplevel")[0])
    # The ansible subdirectory of a parent repository, e.g. an inventory with collections in a submodule.
    if not (project / "ansible.cfg").exists() and (project / "ansible").is_dir():
        project /= "ansible"
    os.chdir(project)
    return [path if os.path.isabs(path) else os.path.relpath(os.path.join(cwd, path)) for path in paths]


def git_latest_release_tag(ref: str = "HEAD", *, exact: bool = False) -> Optional[str]:
    match_kind = "--exact-match" if exact else "--abbrev=0"
    git_describe = f"git describe --tags {match_kind} --match={shlex.quote(RELEASE_TAG_GLOB)} -- {shlex.quote(ref)}"
    result = run_shell_get_lines(f"{git_describe} 2>/dev/null || true")
    return result[0] if result else None


def git_previous_release_tag() -> Optional[str]:
    release = git_latest_release_tag("HEAD", exact=True)
    # Untagged commits since the latest release.
    if release is None:
        return git_latest_release_tag("HEAD")
    # Uncommited changes since the HEAD release.
    if git_changed_paths(release):
        return release
    # Pristine HEAD release, rewind to the previous release.
    return git_latest_release_tag(f"{release}^")


def git_changed_paths(ref: str = "HEAD") -> List[str] | NoReturn:
    # Untracked files are always listed relative to and limited to the current directory, make the diff relative too.
    git_diff_files = (
        f"git diff -z --name-only --no-renames --relative {shlex.quote(ref)} -- "
        "&& git ls-files -z --others --exclude-standard"
    )
    return run_shell_get_lines(git_diff_files, null_delimited=True, unique=True)


def git_ls_files(pathspecs: Iterable[str]) -> List[str] | NoReturn:
    if not isinstance(pathspecs, Iterable) or isinstance(pathspecs, (str, bytes)):
        raise TypeError("testlib.git_ls_files: pathspecs is not an iterable, or is a string or bytes")

    # Tracked files deleted from the work tree are still listed; keep only existing files, following symlinks.
    git_ls_files_cmd = "git ls-files -z -c -o --exclude-standard --deduplicate -- " + shlex.join(pathspecs)
    return [
        path for path in run_shell_get_lines(git_ls_files_cmd, null_delimited=True, unique=True) if os.path.isfile(path)
    ]


def git_ls_files_with_interpreters(pathspecs: Iterable[str], interpreters: Iterable[str]) -> List[str] | NoReturn:
    scripts = [path for path in git_ls_files(SCRIPT_PATHSPECS) if has_shebang(path, interpreters)]
    return sorted(dict.fromkeys(git_ls_files(pathspecs) + scripts))


def has_shebang(path: Path | str, interpreters: Iterable[str]) -> bool | NoReturn:
    if not isinstance(path, (Path, str)):
        raise TypeError("testlib.has_shebang: path is not a Path or string")
    if not isinstance(interpreters, Iterable) or isinstance(interpreters, (str, bytes)):
        raise TypeError("testlib.has_shebang: interpreters is not an iterable, or is a string or bytes")

    names = b"|".join(re.escape(name.encode()) for name in interpreters)
    pattern = rb"#!\s*\S*/(?:env\s+(?:-\S*\s+)*)?(?:" + names + rb")(?:\s.*)?"
    try:
        with open(path, "rb") as f:
            first_line = f.readline(256).rstrip()
    except OSError as err:
        error_code(f"testlib.has_shebang: cannot read {path}: {err}", sys_exit=True)
    return re.fullmatch(pattern, first_line) is not None

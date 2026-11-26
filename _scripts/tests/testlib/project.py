# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import re
import shlex

from fnmatch import fnmatchcase
from pathlib import Path, PurePath
from typing import Iterable, List, NoReturn, Optional, Sequence, Tuple

from .runner import error_code, print_hint, run_shell_get_lines
from .utils import ProjectPath

__all__ = [
    "RELEASE_TAG_GLOB",
    "SCRIPT_PATHSPECS",
    "PYTHON_INTERPRETERS",
    "PYTHON_PATHSPECS",
    "SHELL_INTERPRETERS",
    "SHELL_PATHSPECS",
    "chdir_project",
    "git_latest_release_tag",
    "git_previous_release_with_changes",
    "git_changed_paths",
    "git_ls_files",
    "git_ls_files_with_interpreters",
    "has_shebang",
    "match_paths",
    "select_given_paths",
    "select_given_fqcns",
    "select_changed_paths",
]

RELEASE_TAG_GLOB = "[0-9]*.[0-9]*.[0-9]*"

# Executable scripts without a file extension, identified by their shebang.
SCRIPT_PATHSPECS = ("**scripts/*", "**/bin/*", "**/sbin/*", ":!:*.j2", ":!:*.jinja2", ":!:*.jinja")

PYTHON_INTERPRETERS = ("python", "python3")
PYTHON_PATHSPECS = ("*.py",)

SHELL_INTERPRETERS = ("sh", "bash", "ksh", "zsh")
SHELL_PATHSPECS = (*(f"*.{i}" for i in SHELL_INTERPRETERS), "**/*shrc", "**/.*profile")


# Change to the project directory like run-tests.sh, and rebase paths relative to it; outside paths stay absolute.
def chdir_project(paths: Iterable[Path | str] = ()) -> List[ProjectPath] | NoReturn:
    resolved_paths = [ProjectPath(path).lexical_absolute() for path in paths]
    project = Path(run_shell_get_lines("git rev-parse --show-toplevel")[0])
    if not (project / "ansible.cfg").exists() and (project / "ansible").is_dir():
        project /= "ansible"
    os.chdir(project)
    return [path.relative_to_cwd() for path in resolved_paths]


def git_latest_release_tag(ref: str = "HEAD", *, exact: bool = False) -> Optional[str]:
    match_kind = "--exact-match" if exact else "--abbrev=0"
    git_describe = f"git describe --tags {match_kind} --match={shlex.quote(RELEASE_TAG_GLOB)} -- {shlex.quote(ref)}"
    result = run_shell_get_lines(f"{git_describe} 2>/dev/null || true")
    return result[0] if result else None


def git_previous_release_with_changes() -> Optional[Tuple[str, List[ProjectPath]]] | NoReturn:
    release = git_latest_release_tag("HEAD", exact=True)
    if release is not None:
        # Uncommited changes since the HEAD release.
        if changed_paths := git_changed_paths(release):
            return release, changed_paths

        # Pristine HEAD release, rewind to the previous release.
        release = git_latest_release_tag(f"{release}^")
    else:
        # Untagged commits since the latest release.
        release = git_latest_release_tag("HEAD")
    return (release, git_changed_paths(release)) if release is not None else None


def git_changed_paths(ref: str = "HEAD") -> List[ProjectPath] | NoReturn:
    # Untracked files are always listed relative to and limited to the current directory, make the diff relative too.
    git_diff_files = (
        f"git diff -z --name-only --no-renames --relative {shlex.quote(ref)} -- "
        "&& git ls-files -z --others --exclude-standard"
    )
    return [ProjectPath(path) for path in run_shell_get_lines(git_diff_files, null_delimited=True, unique=True)]


def git_ls_files(pathspecs: Iterable[str]) -> List[ProjectPath] | NoReturn:
    if not isinstance(pathspecs, Iterable) or isinstance(pathspecs, (str, bytes)):
        raise TypeError("testlib.git_ls_files: pathspecs is not an iterable, or is a string or bytes")

    # Tracked files deleted from the work tree are still listed; keep only existing files, following symlinks.
    git_ls_files_cmd = "git ls-files -z -c -o --exclude-standard --deduplicate -- " + shlex.join(pathspecs)
    return [
        ProjectPath(path)
        for path in run_shell_get_lines(git_ls_files_cmd, null_delimited=True, unique=True)
        if os.path.isfile(path)
    ]


def git_ls_files_with_interpreters(
    pathspecs: Iterable[str], interpreters: Iterable[str]
) -> List[ProjectPath] | NoReturn:
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


# Paths matching any pattern: a file path, or a directory path with a trailing slash for everything below it.
# Wildcards of fnmatch match within a single path component.
def match_paths(paths: Iterable[Path], patterns: Iterable[str]) -> List[Path]:
    compiled = [(PurePath(pattern).parts, pattern.endswith("/")) for pattern in patterns]

    def is_match(parts: Sequence[str]) -> bool:
        return any(
            (len(parts) > len(pattern_parts) if is_dir else len(parts) == len(pattern_parts))
            and all(fnmatchcase(part, pattern_part) for part, pattern_part in zip(parts, pattern_parts))
            for pattern_parts, is_dir in compiled
        )

    return [path for path in paths if is_match(path.parts)]


def select_given_paths(given: List[Path | str], select_all: bool) -> Optional[List[ProjectPath]] | NoReturn:
    if select_all and given:
        error_code("--all cannot be combined with paths.", sys_exit=True)
    if select_all:
        print_hint("Selected everything from the command line.")
        return None  # Everything.
    if given:
        print_hint(f"Selected {len(given)} path(s) from the command line.")
        return [ProjectPath(path) for path in given]
    return []  # Nothing.


def select_given_fqcns(given: List[str], select_all: bool) -> Optional[List[str]] | NoReturn:
    if select_all and given:
        error_code("--all cannot be combined with FQCNs.", sys_exit=True)
    if select_all:
        print_hint("Selected everything from the command line.")
        return None  # Everything.
    if given:
        print_hint(f"Selected {len(given)} FQCN(s) from the command line.")
        return given
    return []  # Nothing.


def select_changed_paths(
    framework_patterns: Iterable[str], ignore_framework: bool = False, require_release: bool = False
) -> Optional[List[ProjectPath]] | NoReturn:
    release_with_changes = git_previous_release_with_changes()
    if release_with_changes is None:
        if require_release:
            error_code("No release tag found. Wrong repository?", sys_exit=True)
        print_hint("No release tag found, selected everything.")
        return None  # Everything.

    release, changed_paths = release_with_changes
    print_hint(f"Changes since release {release} affect {len(changed_paths)} path(s).")

    if framework_changes := match_paths(changed_paths, framework_patterns):
        effect = "are ignored" if ignore_framework else "select everything"
        print_hint(f"Framework changes {effect}:", *framework_changes)
        changed_paths = (
            [path for path in changed_paths if path not in framework_changes]
            if ignore_framework
            else None  # Everything.
        )
    return changed_paths

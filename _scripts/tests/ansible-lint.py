#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import os

from argparse import ArgumentParser, REMAINDER
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Optional, Tuple

from testlib import (
    RC,
    error_code,
    git_changed_paths,
    git_previous_release_tag,
    print_hint,
    print_success,
    run_tests,
)

args_parser = ArgumentParser(
    usage="ansible-lint.py [--help] [--all] [PATHS ...] [-- ANSIBLE_LINT_ARGS ...]",
    description="Run ansible-lint on the paths changed since the previous release, on the given paths, or on everything.",
    epilog="Arguments after -- are passed to ansible-lint verbatim.",
)

args_parser.add_argument("--all", help="lint everything", action="store_true")
args_parser.add_argument("paths", help="[PATHS ...] [-- ANSIBLE_LINT_ARGS ...]", nargs=REMAINDER)


def _lint_path(path: str) -> Optional[str]:
    """Role directory of a path within a role, the path itself, or None if it no longer exists."""
    parts = Path(path).parts
    if "roles" in parts:
        index = parts.index("roles")
        if len(parts) > index + 2:
            path = str(Path(*parts[: index + 2]))
    return path if os.path.lexists(path) else None


def _changed_lint_paths(paths: Iterable[str], ansible_lint_args: List[str]) -> List[str]:
    """Unique paths to lint for the changed paths."""
    # Import after main configures Ansible's temporary directory and vault environment.
    from ansiblelint.cli import get_config  # pylint: disable=import-outside-toplevel
    from ansiblelint.file_utils import discover_lintables  # pylint: disable=import-outside-toplevel

    # Explicit lint targets bypass exclusions; use normal discovery to filter automatic targets.
    options = get_config([*ansible_lint_args, "--"])
    discovered_paths = {_lint_path(path) for path in discover_lintables(options)}
    lint_paths = {
        lint_path for path in paths if (lint_path := _lint_path(path)) is not None and lint_path in discovered_paths
    }
    return sorted(lint_paths)


def select_paths(app_args, ansible_lint_args: List[str]) -> Tuple[Optional[List[str]], List[str]]:
    """Paths from the CLI, the paths changed since the previous release, or None for everything."""
    paths = app_args.paths
    if "--" in paths:
        paths = paths[: paths.index("--")]
    if app_args.all:
        if paths:
            error_code("ansible-lint.py --all cannot be combined with PATHS.", sys_exit=True)
        return None, ["Selected everything."]

    if paths:
        return paths, [f"Selected {len(paths)} path(s) from the command line."]

    release = git_previous_release_tag()
    if release is None:
        return None, ["No release tag found, selected everything."]

    # Relative to the current directory, which may be a subdirectory of a parent repository.
    lint_paths = _changed_lint_paths(git_changed_paths(release, relative=True), ansible_lint_args)
    return lint_paths, [f"Changes since release {release} affect {len(lint_paths)} path(s)."]


def main() -> None:
    app_args = args_parser.parse_args()
    ansible_lint_args = app_args.paths[app_args.paths.index("--") + 1 :] if "--" in app_args.paths else []

    # Update the env dict directly, so ansible-lint also uses it in _changed_lint_paths.
    os.environ.update(dict.fromkeys(("ANSIBLE_ASK_VAULT_PASS", "ANSIBLE_ASK_PASS", "ANSIBLE_BECOME_ASK_PASS"), "False"))

    tempdir = TemporaryDirectory(prefix="ansible-lint-")  # pylint: disable=consider-using-with
    vault_dummy = os.path.join(tempdir.name, "vault-password-dummy")
    with open(vault_dummy, "w", encoding="utf-8") as f:
        f.write("dummy")

    # Disable vault scripts as nothing needs to be decrypted for linting.
    os.environ["ANSIBLE_VAULT_PASSWORD_FILE"] = vault_dummy
    os.environ["ANSIBLE_VAULT_IDENTITY_LIST"] = vault_dummy

    # Change ansible temp directory for read-only, agentic environments.
    os.environ.setdefault("ANSIBLE_LOCAL_TEMP", tempdir.name)

    paths, notes = select_paths(app_args, ansible_lint_args)
    for note in notes:
        print_hint(note)

    if paths == []:
        print_success("ansible-lint: nothing to lint!")
        RC.status(RC.OK, sys_exit=True)

    run_tests(["ansible-lint", *ansible_lint_args, "--"], targets=paths or [], sys_exit=True)


if __name__ == "__main__":
    main()

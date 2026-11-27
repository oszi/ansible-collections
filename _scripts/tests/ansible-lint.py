#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import glob
import os
import sys

from argparse import ArgumentParser, Namespace
from tempfile import TemporaryDirectory
from typing import Iterable, List, Optional

from testlib import (
    ANSIBLE_NO_PROMPT_ENV,
    ProjectPath,
    chdir_project,
    print_debug,
    run_tests,
    select_changed_paths,
    select_given_paths,
    split_passthrough_args,
)

ANSIBLE_LINT_CMD = ["ansible-lint"]

# Changes to the lint configuration and tooling affect every lintable path,
# besides the active config file, ignore file and rules directories.
FRAMEWORK_PATTERNS = (
    "_scripts/tests/ansible-lint.py",
    ".ansible-lint*",
    ".config/ansible-lint*",
    "ansible.cfg",
    "requirements.txt",
    "requirements.yml",
)

args_parser = ArgumentParser(
    usage="ansible-lint.py [--help] [--all] [PATHS ...] [-- ANSIBLE_LINT_ARGS ...]",
    description="Run ansible-lint on the paths changed since the previous release, on the given paths, or on everything.",
    epilog="Arguments after -- are passed to ansible-lint verbatim.",
)

args_parser.add_argument("--all", help="lint everything", action="store_true")
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def _lint_options(ansible_lint_args: List[str]) -> Namespace:
    """ansible-lint options of the arguments and its configuration file."""
    # Import after main configures Ansible's temporary directory and vault environment.
    from ansiblelint.cli import get_config  # pylint: disable=import-outside-toplevel

    return get_config([*ansible_lint_args, "--"])


def _framework_patterns(options: Namespace) -> List[str]:
    """Patterns of the lint configuration and tooling, including the active config and ignore files and rules directories."""
    config_files = tuple(
        str(ProjectPath(path).relative_to_cwd()) for path in (options.config_file, options.ignore_file) if path
    )
    # Rules directories outside the project, e.g. of installed packages, are not tracked.
    rulesdirs = tuple(
        f"{rulesdir}/"
        for path in options.rulesdirs
        if not (rulesdir := ProjectPath(path).relative_to_cwd()).is_absolute()
    )
    return [*FRAMEWORK_PATTERNS, *map(glob.escape, config_files + rulesdirs)]


def _changed_lint_paths(paths: Iterable[ProjectPath], options: Namespace) -> List[ProjectPath]:
    """Unique paths to lint for the changed paths."""
    from ansiblelint.file_utils import discover_lintables  # pylint: disable=import-outside-toplevel

    # Explicit lint targets bypass exclusions; use normal discovery to filter automatic targets.
    # Deleted files select their role, if the role is still lintable, as references may break.
    discovered_paths = {ProjectPath(path) for path in discover_lintables(options)}
    # Excludes roles outside the collections; parent repositories without release tags select everything.
    discovered_roles = {role_dir for path in discovered_paths if (role_dir := path.collection_role_dir) is not None}

    lint_paths = set()
    excluded_paths = []
    for path in paths:
        role_dir = path.collection_role_dir
        if path in discovered_paths:
            lint_paths.add(role_dir or path)
        elif role_dir in discovered_roles and not os.path.exists(path):
            lint_paths.add(role_dir)
        else:
            excluded_paths.append(path)

    if excluded_paths:
        print_debug("Changed path(s) excluded by lint discovery:", excluded_paths)
    return sorted(lint_paths)


def select_paths(app_args: Namespace, ansible_lint_args: List[str]) -> Optional[List[ProjectPath]]:
    """Paths from the CLI, the paths changed since the previous release, or None for everything."""
    selected_paths = select_given_paths(app_args.paths, app_args.all)
    if selected_paths == []:  # Nothing given.
        options = _lint_options(ansible_lint_args)
        selected_paths = select_changed_paths(_framework_patterns(options))
        if selected_paths:
            return _changed_lint_paths(selected_paths, options)
    return selected_paths  # None for everything.


def main() -> None:
    own_args, ansible_lint_args = split_passthrough_args(sys.argv[1:])
    app_args = args_parser.parse_intermixed_args(own_args)
    app_args.paths = chdir_project(app_args.paths)

    # Update the env dict directly, so ansible-lint also uses it in _changed_lint_paths.
    os.environ.update(ANSIBLE_NO_PROMPT_ENV)

    tempdir = TemporaryDirectory(prefix="ansible-lint-")  # pylint: disable=consider-using-with
    vault_dummy = os.path.join(tempdir.name, "vault-password-dummy")
    with open(vault_dummy, "w", encoding="utf-8") as f:
        f.write("dummy")

    # Disable vault scripts as nothing needs to be decrypted for linting.
    os.environ["ANSIBLE_VAULT_PASSWORD_FILE"] = vault_dummy
    os.environ["ANSIBLE_VAULT_IDENTITY_LIST"] = vault_dummy

    # Change ansible temp directory for read-only, agentic environments.
    os.environ.setdefault("ANSIBLE_LOCAL_TEMP", tempdir.name)

    paths = select_paths(app_args, ansible_lint_args)
    run_tests(ANSIBLE_LINT_CMD + ansible_lint_args + ["--"], paths, sys_exit=True)


if __name__ == "__main__":
    main()

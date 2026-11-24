#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import os
import sys

from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Optional, Tuple

from testlib import (
    chdir_project,
    error_code,
    git_changed_paths,
    git_previous_release_tag,
    print_hint,
    run_tests,
    split_passthrough_args,
)

ANSIBLE_LINT_CMD = ["ansible-lint"]

# Changes to the lint configuration and tooling affect every lintable path,
# besides the active config file, ignore file and rules directories.
CONFIG_PATHS = (
    "_scripts/tests/ansible-lint.py",
    ".ansible-lint",
    "ansible.cfg",
    "requirements.txt",
    "requirements.yml",
)

HINT_PATHS_MAX = 20

args_parser = ArgumentParser(
    usage="ansible-lint.py [--help] [--all] [PATHS ...] [-- ANSIBLE_LINT_ARGS ...]",
    description="Run ansible-lint on the paths changed since the previous release, on the given paths, or on everything.",
    epilog="Arguments after -- are passed to ansible-lint verbatim.",
)

args_parser.add_argument("--all", help="lint everything", action="store_true")
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def _role_path(path: str) -> Optional[str]:
    """Role directory of a path within a role, or None."""
    parts = Path(path).parts
    if "roles" in parts and len(parts) > (index := parts.index("roles")) + 2:
        return str(Path(*parts[: index + 2]))
    return None


def _changed_lint_paths(paths: Iterable[str], ansible_lint_args: List[str]) -> Tuple[Optional[List[str]], List[str]]:
    """Unique paths to lint for the changed paths, or None for everything; and the configuration changes."""
    # Import after main configures Ansible's temporary directory and vault environment.
    from ansiblelint.cli import get_config  # pylint: disable=import-outside-toplevel
    from ansiblelint.file_utils import discover_lintables  # pylint: disable=import-outside-toplevel
    from ansiblelint.loaders import IGNORE_FILE  # pylint: disable=import-outside-toplevel

    options = get_config([*ansible_lint_args, "--"])
    config_files = {
        *CONFIG_PATHS,
        *IGNORE_FILE,
        *(os.path.relpath(path) for path in (options.config_file, options.ignore_file) if path),
    }
    rulesdirs = tuple(
        f"{rulesdir}/" for path in options.rulesdirs if not (rulesdir := os.path.relpath(path)).startswith("..")
    )
    if config_changes := [path for path in paths if path in config_files or path.startswith(rulesdirs)]:
        return None, config_changes

    # Explicit lint targets bypass exclusions; use normal discovery to filter automatic targets.
    # Deleted files select their role, if the role is still lintable, as references may break.
    discovered_paths = set(discover_lintables(options))
    discovered_roles = {role_path for path in discovered_paths if (role_path := _role_path(path)) is not None}
    lint_paths = set()
    for path in paths:
        role_path = _role_path(path)
        if path in discovered_paths:
            lint_paths.add(role_path or path)
        elif role_path in discovered_roles and not os.path.exists(path):
            lint_paths.add(role_path)
    return sorted(lint_paths), []


def select_paths(app_args, ansible_lint_args: List[str]) -> Tuple[Optional[List[str]], List[str]]:
    """Paths from the CLI, the paths changed since the previous release, or None for everything."""
    paths = app_args.paths
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
    lint_paths, config_changes = _changed_lint_paths(git_changed_paths(release), ansible_lint_args)
    if lint_paths is None:
        changes = "\n# ".join(["Configuration changes affect everything:", *config_changes])
        return None, [f"Changes since release {release} select everything.", changes]

    notes = [f"Changes since release {release} affect {len(lint_paths)} lintable path(s)."]
    if 0 < len(lint_paths) <= HINT_PATHS_MAX:
        changes = "\n# ".join(["Affected lintable path(s):", *lint_paths])
        notes.append(changes)
    return lint_paths, notes


def main() -> None:
    own_args, ansible_lint_args = split_passthrough_args(sys.argv[1:])
    app_args = args_parser.parse_intermixed_args(own_args)
    app_args.paths = chdir_project(app_args.paths)

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

    run_tests(ANSIBLE_LINT_CMD + ansible_lint_args + ["--"], paths, sys_exit=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import os

from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Set

from testlib import (
    NAMESPACE_PATH,
    RC,
    Color,
    Output,
    all_collection_paths,
    chdir_project,
    error_code,
    git_changed_paths,
    git_previous_release_tag,
    nothing_to_test,
    print_hint,
    require_commands,
    run_test_cmd,
    run_tests_parallel,
)

UNIT_TESTS_PATH = Path("tests") / "unit"

# Module directories embedded in roles and next to playbooks, besides *_plugins.
EMBEDDED_PLUGIN_DIRS = ("library", "module_utils")

ANSIBLE_TEST_CMD = ["ansible-test"]
ANSIBLE_TEST_ARGS = [
    "--docker=default",
    f"--color={'yes' if Color.COLORS_ENABLED else 'no'}",
]

COMMANDS = ("sanity", "units")

# Changes to the tooling, e.g. the ansible-core version, affect every collection.
FRAMEWORK_PATHS = (
    "_scripts/tests/ansible-test.py",
    "requirements.txt",
)

args_parser = ArgumentParser(
    usage="ansible-test.py [--help] [--all] [--sanity] [--units] [PATHS ...]",
    description="Run whole-collection ansible-test suites for changes since the previous release, "
    "for the given paths, or for everything.",
    epilog="Any collection path selects sanity; plugin/module sources, unit tests or their parent directories "
    "also select units.",
)

args_parser.add_argument("--all", help="test everything", action="store_true")

args_parser.add_argument(
    "--sanity", help="run only ansible-test sanity, unless --units is also given", action="store_true"
)
args_parser.add_argument(
    "--units", help="run only ansible-test units, unless --sanity is also given", action="store_true"
)
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def lexical_path(path_str: str) -> Path:
    # Keep the final component unresolved, so symlinks belong to the collection containing them.
    path = Path(os.path.abspath(path_str))
    return path.parent.resolve() / path.name if path.name else path


def is_plugin_path(target: Path) -> bool:
    """Collection plugin/module sources, including embedded role and playbook sources."""
    parts = target.parts
    if parts[:1] == ("plugins",):
        return True
    for depth, parent in ((3, "roles"), (2, "playbooks")):
        if len(parts) >= depth and parts[0] == parent:
            name = parts[depth - 1]
            if name in EMBEDDED_PLUGIN_DIRS or name.endswith("_plugins"):
                return True
    return False


def select_targets(paths: List[str], commands: List[str]) -> Dict[str, Set[Path]]:
    """Whole collections per suite; sources, unit tests and their parent directories select units."""
    collections = [collection.resolve() for collection in all_collection_paths() if collection.is_dir()]
    selected: Dict[str, Set[Path]] = {command: set() for command in commands}
    for path_str in paths:
        path = lexical_path(path_str)
        collection = next((collection for collection in collections if path.is_relative_to(collection)), None)
        if collection is None:
            error_code(f"{path_str} is not in a collection of {NAMESPACE_PATH}!", sys_exit=True)

        target = path.relative_to(collection)

        if "sanity" in selected:
            selected["sanity"].add(collection)

        if (
            "units" in selected
            and (collection / UNIT_TESTS_PATH).is_dir()
            and (
                is_plugin_path(target)
                or target.is_relative_to(UNIT_TESTS_PATH)
                or UNIT_TESTS_PATH.is_relative_to(target)
            )
        ):
            selected["units"].add(collection)

    return selected


def select_paths(app_args) -> List[str]:
    """Paths from the CLI, the paths affected by changes since the previous release, or every collection."""
    if app_args.all and app_args.paths:
        error_code("ansible-test.py --all cannot be combined with PATHS.", sys_exit=True)
    if app_args.paths:
        print_hint(f"Selected {len(app_args.paths)} path(s) from the command line.")
        return app_args.paths

    all_paths = [str(path) for path in all_collection_paths() if path.is_dir()]
    if not all_paths:
        print_hint(f"No collections of {NAMESPACE_PATH} in {os.getcwd()}.")
        return []
    if app_args.all:
        print_hint("Selected everything.")
        return all_paths

    release = git_previous_release_tag()
    if release is None:
        print_hint("No release tag found, selected everything.")
        return all_paths

    # Relative to the current directory, which may be a subdirectory of a parent repository.
    changed_paths = git_changed_paths(release)
    print_hint(f"Selected changes since release {release}.")
    if framework_changes := [path for path in changed_paths if path in FRAMEWORK_PATHS]:
        print_hint("Framework changes affect every collection:", *framework_changes)
        return all_paths

    return [path for path in changed_paths if any(Path(path).is_relative_to(collection) for collection in all_paths)]


def prepare_containers(cwd: str) -> int:
    # Parallel jobs race on a cold image store and on creating ~/.ansible/test/id_rsa, which --prime-containers
    # does not create; one serial container start pulls the image and creates the key pair.
    prepare_cmd = ANSIBLE_TEST_CMD + ["shell"]
    return run_test_cmd(
        prepare_cmd + ANSIBLE_TEST_ARGS + ["--", "true"],
        [],
        "ansible-test prepare containers",
        cwd=cwd,
        output=Output.ON_FAILURE_QUIET,
    )


def main() -> None:
    app_args = args_parser.parse_args()
    app_args.paths = chdir_project(app_args.paths)
    commands = [command for command in COMMANDS if getattr(app_args, command)] or list(COMMANDS)

    paths = select_paths(app_args)
    selected = select_targets(paths, commands)
    if not any(selected.values()):
        nothing_to_test(ANSIBLE_TEST_CMD[0], sys_exit=True)

    jobs = [
        {
            "args": [command, *ANSIBLE_TEST_ARGS],
            "cwd": str(collection),
            "subject": f"{ANSIBLE_TEST_CMD[0]} {command}: {NAMESPACE_PATH.name}.{collection.name}",
        }
        for command, selection in selected.items()
        for collection in sorted(selection)
    ]

    require_commands(ANSIBLE_TEST_CMD[0])
    if (rc := prepare_containers(jobs[0]["cwd"])) != RC.OK:
        RC.status(rc, sys_exit=True)

    rc = run_tests_parallel(ANSIBLE_TEST_CMD, jobs)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()

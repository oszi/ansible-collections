#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import os
import shutil

from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Set, Tuple

from testlib import (
    NAMESPACE_PATH,
    RC,
    Color,
    Output,
    all_collection_paths,
    error_code,
    git_changed_paths,
    git_previous_release_tag,
    print_hint,
    print_success,
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


def select_paths(app_args) -> Tuple[List[str], List[str]]:
    """Paths from the CLI, the paths affected by changes since the previous release, or every collection."""
    all_paths = [str(path) for path in all_collection_paths() if path.is_dir()]
    if app_args.all:
        if app_args.paths:
            error_code("ansible-test.py --all cannot be combined with PATHS.", sys_exit=True)
        return all_paths, ["Selected everything."]

    if app_args.paths:
        return app_args.paths, [f"Selected {len(app_args.paths)} path(s) from the command line."]

    release = git_previous_release_tag()
    if release is None:
        return all_paths, ["No release tag found, selected everything."]

    # Relative to the current directory, which may be a subdirectory of a parent repository.
    paths = [
        path
        for path in git_changed_paths(release)
        if any(Path(path).is_relative_to(collection) for collection in all_paths)
    ]
    return paths, [f"Selected changes since release {release}."]


def prepare_containers(collection: Path) -> int:
    # Parallel jobs race on a cold image store and on creating ~/.ansible/test/id_rsa, which --prime-containers
    # does not create; one serial container start pulls the image and creates the key pair.
    prepare_cmd = ANSIBLE_TEST_CMD + ["shell"]
    return run_test_cmd(
        prepare_cmd + ANSIBLE_TEST_ARGS + ["--", "true"],
        [],
        "ansible-test prepare containers",
        cwd=str(collection),
        output=Output.ON_FAILURE_QUIET,
    )


def main() -> None:
    app_args = args_parser.parse_args()
    commands = [command for command in COMMANDS if getattr(app_args, command)] or list(COMMANDS)

    paths, notes = select_paths(app_args)
    for note in notes:
        print_hint(note)

    selected = select_targets(paths, commands)
    if not any(selected.values()):
        print_success("ansible-test: nothing to test!")
        RC.status(RC.OK, sys_exit=True)

    if shutil.which(ANSIBLE_TEST_CMD[0]) is None:
        error_code("ansible-test not found! `source venv/bin/activate`", sys_exit=True)

    jobs = [
        {
            "args": [command, *ANSIBLE_TEST_ARGS],
            "cwd": str(collection),
            "subject": f"{ANSIBLE_TEST_CMD[0]} {command}: {NAMESPACE_PATH.name}.{collection.name}",
        }
        for command, selection in selected.items()
        for collection in sorted(selection)
    ]

    if (rc := prepare_containers(NAMESPACE_PATH / "utils")) != RC.OK:
        RC.status(rc, sys_exit=True)

    rc = run_tests_parallel(ANSIBLE_TEST_CMD, jobs)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()

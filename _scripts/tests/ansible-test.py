#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Set, Tuple

from testlib import (
    NAMESPACE_PATH,
    Color,
    Output,
    ProjectPath,
    RC,
    chdir_project,
    error_code,
    nothing_to_test,
    require_commands,
    run_test_cmd,
    run_tests_parallel,
    select_changed_paths,
    select_given_paths,
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
FRAMEWORK_PATTERNS = (
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


def is_plugin_target_path(target: Path) -> bool:
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


def select_targets(paths: List[ProjectPath], commands: Tuple[str, ...]) -> Dict[str, Set[ProjectPath]]:
    """Whole collections per suite; sources, unit tests and their parent directories select units."""
    selected: Dict[str, Set[ProjectPath]] = {command: set() for command in commands}
    for path in paths:
        if (collection := path.collection_dir) is None:
            continue
        target = path.relative_to(collection)

        if "sanity" in selected:
            selected["sanity"].add(collection)

        if (
            "units" in selected
            and (collection / UNIT_TESTS_PATH).is_dir()
            and (
                is_plugin_target_path(target)
                or target.is_relative_to(UNIT_TESTS_PATH)
                or UNIT_TESTS_PATH.is_relative_to(target)
            )
        ):
            selected["units"].add(collection)

    return selected


def select_paths(app_args) -> List[ProjectPath]:
    """Collection paths of the selection; every collection for everything."""
    selected_paths = select_given_paths(app_args.paths, app_args.all)
    if selected_paths:
        for path in selected_paths:
            if not path.collection_dir:
                error_code(f"{path} is not in a collection of {NAMESPACE_PATH}!", sys_exit=True)
        return selected_paths

    if selected_paths == []:  # Nothing given.
        selected_paths = select_changed_paths(FRAMEWORK_PATTERNS)
    if selected_paths is None:  # Everything.
        return ProjectPath.all_collections()  # Empty in parent repositories.
    return [path for path in selected_paths if path.collection_dir]


def prepare_containers(cwd: ProjectPath | str) -> int:
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
    commands = tuple(command for command in COMMANDS if getattr(app_args, command)) or COMMANDS
    selected = select_targets(select_paths(app_args), commands)
    jobs = [
        {
            "args": [command, *ANSIBLE_TEST_ARGS],
            "cwd": collection_dir,
            "subject": f"{ANSIBLE_TEST_CMD[0]} {command}: {collection_dir.collection_fqcn}",
        }
        for command, collections in selected.items()
        for collection_dir in sorted(collections)
    ]

    if not jobs:
        nothing_to_test(ANSIBLE_TEST_CMD[0], sys_exit=True)

    require_commands(ANSIBLE_TEST_CMD[0])
    if (rc := prepare_containers(jobs[0]["cwd"])) != RC.OK:
        RC.status(rc, sys_exit=True)

    rc = run_tests_parallel(ANSIBLE_TEST_CMD, jobs)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()

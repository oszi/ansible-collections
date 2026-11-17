#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import importlib.util
import shutil
import sys

from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Optional

from testlib import NAMESPACE_PATH, RC, Color, Output, error_code, print_success, run_test_cmd, run_tests_parallel

UNIT_TESTS_PATH = Path("tests") / "unit"

ANSIBLE_TEST_CMD = ["ansible-test"]
ANSIBLE_TEST_ARGS = [
    "--local",
    f"--python-interpreter={sys.executable}",
    f"--color={'yes' if Color.COLORS_ENABLED else 'no'}",
]

COMMANDS = ("sanity", "units")

args_parser = ArgumentParser(
    usage="ansible-test.py [--help] [--sanity] [--units] [PATHS...]",
    description="Run ansible-test sanity and units tests of the collections.",
    epilog="PATHS select collections, files or directories; plugin source paths select all unit tests.",
)

args_parser.add_argument(
    "--sanity", help="run only ansible-test sanity, unless --units is also given", action="store_true"
)
args_parser.add_argument(
    "--units", help="run only ansible-test units, unless --sanity is also given", action="store_true"
)
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")

# Collection paths mapped to ansible-test targets; an empty list selects the whole collection.
Selection = Dict[Path, List[str]]


def all_collections() -> List[Path]:
    return [path.parent for path in sorted(NAMESPACE_PATH.glob("[a-zA-Z]*/galaxy.yml"))]


def add_target(selection: Selection, collection: Path, target: Optional[str]) -> None:
    if target is None:
        selection[collection] = []
    elif collection not in selection:
        selection[collection] = [target]
    elif selection[collection]:
        selection[collection].append(target)


def target_arg(path: Path, target: Path) -> Optional[str]:
    if target == Path("."):
        return None
    # ansible-test matches directory targets only with a trailing separator.
    return f"{target.as_posix()}/" if path.is_dir() else target.as_posix()


def select_targets(paths: List[str], commands: List[str]) -> Dict[str, Selection]:
    collections = [collection.resolve() for collection in all_collections()]
    selected: Dict[str, Selection] = {command: {} for command in commands}
    for path_str in paths:
        path = Path(path_str).resolve()
        collection = next((collection for collection in collections if path.is_relative_to(collection)), None)
        if collection is None:
            error_code(f"{path_str} is not in a collection of {NAMESPACE_PATH}!", sys_exit=True)

        target = path.relative_to(collection)
        arg = target_arg(path, target)

        if "sanity" in selected:
            add_target(selected["sanity"], collection, arg)

        if "units" in selected and (collection / UNIT_TESTS_PATH).is_dir():
            # Plugin tests can cover shared dependencies and need not mirror source filenames.
            if UNIT_TESTS_PATH.is_relative_to(target) or target.is_relative_to("plugins"):
                add_target(selected["units"], collection, None)
            elif target.is_relative_to(UNIT_TESTS_PATH):
                add_target(selected["units"], collection, arg)

    return selected


def prime_sanity_venvs(collection: Path) -> int:
    # Sanity virtualenvs are shared in ~/.ansible/test/venv and rebuilt in place when incomplete,
    # so parallel sanity jobs would race on a cold cache; create them once beforehand.
    return run_test_cmd(
        ANSIBLE_TEST_CMD + ["sanity", "--prime-venvs", *ANSIBLE_TEST_ARGS],
        [],
        "ansible-test sanity --prime-venvs",
        cwd=str(collection),
        output=Output.ON_FAILURE_QUIET,
    )


def main() -> None:
    app_args = args_parser.parse_args()
    commands = [command for command in COMMANDS if getattr(app_args, command)] or list(COMMANDS)

    selected = select_targets(app_args.paths or [str(path) for path in all_collections()], commands)
    if not any(selected.values()):
        print_success("ansible-test: nothing to test!")
        RC.status(RC.OK, sys_exit=True)

    missing_pytest = "units" in commands and importlib.util.find_spec("pytest") is None
    if shutil.which(ANSIBLE_TEST_CMD[0]) is None or missing_pytest:
        error_code("ansible-test or pytest not found! `source venv/bin/activate`", sys_exit=True)

    jobs = [
        {
            "args": [command, *ANSIBLE_TEST_ARGS, *targets],
            "cwd": str(collection),
            "subject": " ".join(["ansible-test", f"{command}:", f"{NAMESPACE_PATH.name}.{collection.name}", *targets]),
        }
        for command, selection in selected.items()
        for collection, targets in selection.items()
    ]

    sanity_collections = list(selected.get("sanity", {}))
    if sanity_collections and (rc := prime_sanity_venvs(sanity_collections[0])) != RC.OK:
        RC.status(rc, sys_exit=True)

    rc = run_tests_parallel(ANSIBLE_TEST_CMD, jobs)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()

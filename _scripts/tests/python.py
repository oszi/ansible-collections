#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
import os
import sys

from argparse import ArgumentParser
from tempfile import TemporaryDirectory

from testlib import (
    PYTHON_INTERPRETERS,
    PYTHON_PATHSPECS,
    RC,
    Output,
    chdir_project,
    git_ls_files_with_interpreters,
    print_hint,
    run_tests,
    run_tests_parallel,
)

PYLINT_PY_VERSION = "3.12"
BLACK_PY_VERSION = "py312"

PYLINT_CMD = ["pylint", "--disable=duplicate-code,import-error", f"--py-version={PYLINT_PY_VERSION}", "--"]
BLACK_CMD = ["black", "--check", "-l", "120", f"--target-version={BLACK_PY_VERSION}", "--"]

args_parser = ArgumentParser(
    usage="python.py [--help] [--black] [PATHS...]",
    description="Run pylint and black on python scripts in the repository.",
)

args_parser.add_argument("--black", help="reformat files with black", action="store_true", default=False)
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def main() -> None:
    app_args = args_parser.parse_args()
    paths = chdir_project(app_args.paths) or git_ls_files_with_interpreters(PYTHON_PATHSPECS, PYTHON_INTERPRETERS)
    env = os.environ.copy()

    # Change python cache directory for read-only, agentic environments.
    # XDG_CACHE_HOME is usually unset, implying ~/.cache/...
    if "XDG_CACHE_HOME" not in env:
        tempdir = TemporaryDirectory(prefix="ansible-python-tests-")  # pylint: disable=consider-using-with
        env["XDG_CACHE_HOME"] = tempdir.name

    # Run black live if asked explicitly, otherwise run it in a thread pool one by one which works
    # in restrictive sandboxes that disallow python process pools; see run_tests_parallel.
    if app_args.black:
        black_cmd = BLACK_CMD.copy()
        black_cmd.remove("--check")
        run_tests(black_cmd, paths, env=env, sys_exit=True)

    rc_pylint = run_tests(PYLINT_CMD, paths, env=env)
    rc_black = run_tests_parallel(BLACK_CMD, paths, env=env, output=Output.ON_FAILURE_QUIET)
    if rc_black != RC.OK:
        print_hint(f"{sys.argv[0]} --black")
    RC.select(rc_pylint, rc_black, sys_exit=True)


if __name__ == "__main__":
    main()

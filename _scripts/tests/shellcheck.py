#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
from argparse import ArgumentParser

from testlib import SHELL_INTERPRETERS, SHELL_PATHSPECS, git_ls_files_with_interpreters, run_tests

SHELLCHECK_CMD = ["shellcheck", "--"]

args_parser = ArgumentParser(
    usage="shellcheck.py [--help] [PATHS...]",
    description="Run shellcheck on scripts in the repository.",
)

args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def main() -> None:
    app_args = args_parser.parse_args()
    paths = app_args.paths or git_ls_files_with_interpreters(SHELL_PATHSPECS, SHELL_INTERPRETERS)
    run_tests(SHELLCHECK_CMD, paths, sys_exit=True)


if __name__ == "__main__":
    main()

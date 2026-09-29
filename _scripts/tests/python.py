#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
import os
import sys

from argparse import ArgumentParser
from tempfile import TemporaryDirectory

from testlib import RC, run_shell_get_lines, run_tests, run_tests_parallel, print_hint

GIT_LS_FILES = r"""
set -euo pipefail
git ls-files -c -o --exclude-standard --deduplicate -- '*.py'
git ls-files -c -o --exclude-standard --deduplicate -z -- '**scripts/*' '**/bin/*' '**/sbin/*' ':!:*.'{j2,jinja2,jinja} \
    | xargs -0 -r awk -- 'FNR>1 {nextfile} /^#![^ ]+[/ ](python3?)$/ {print FILENAME; nextfile}'
"""

PYLINT_CMD = ["pylint", "--disable=duplicate-code,import-error", "--"]
BLACK_CMD = ["black", "--check", "-l", "120", "--target-version=py311", "--"]

args_parser = ArgumentParser(
    usage="python.py [--help] [--black] [PATHS...]",
    description="Run pylint and black on python scripts in the repository.",
)

args_parser.add_argument("--black", help="reformat files with black", action="store_true", default=False)
args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def main() -> None:
    app_args = args_parser.parse_args()
    paths = app_args.paths or run_shell_get_lines(GIT_LS_FILES, unique=True)
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
        rc_black = run_tests(black_cmd, paths, env=env)
        sys.exit(rc_black)

    rc_pylint = run_tests(PYLINT_CMD, paths, env=env)
    rc_black = run_tests_parallel(BLACK_CMD, paths, quiet=True, env=env)
    if rc_black != RC.OK:
        print_hint(f"{sys.argv[0]} --black")

    sys.exit(rc_pylint | rc_black)


if __name__ == "__main__":
    main()

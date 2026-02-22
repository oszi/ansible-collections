#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring

import sys

from argparse import ArgumentParser

from utils import run_shell, run_tests


GIT_LS_FILES = r"""
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
    paths = run_shell(GIT_LS_FILES) if not app_args.paths else app_args.paths

    if app_args.black:
        black_cmd = BLACK_CMD.copy()
        black_cmd.remove("--check")
        rc_black = run_tests(black_cmd, paths)
        sys.exit(rc_black)

    rc_pylint = run_tests(PYLINT_CMD, paths)
    rc_black = run_tests(BLACK_CMD, paths)
    sys.exit(rc_pylint | rc_black)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring

import sys

from argparse import ArgumentParser

from utils import run_shell, run_tests


GIT_LS_FILES = r"""
git ls-files -c -o --exclude-standard --deduplicate -- '*.'{sh,bash,ksh,zsh} '**/*shrc' '**/.*profile'
git ls-files -c -o --exclude-standard --deduplicate -z -- '**scripts/*' '**/bin/*' '**/sbin/*' ':!:*.'{j2,jinja2,jinja} \
    | xargs -0 -r awk -- 'FNR>1 {nextfile} /^#![^ ]+[/ ](sh|bash|ksh|zsh)$/ {print FILENAME; nextfile}'
"""

SHELLCHECK_CMD = ["shellcheck", "--"]

args_parser = ArgumentParser(
    usage="shellcheck.py [--help] [PATHS...]",
    description="Run shellcheck on scripts in the repository.",
)

args_parser.add_argument("paths", help="[PATHS ...]", nargs="*")


def main() -> None:
    app_args = args_parser.parse_args()
    paths = run_shell(GIT_LS_FILES) if not app_args.paths else app_args.paths
    rc = run_tests(SHELLCHECK_CMD, paths)
    sys.exit(rc)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring

import sys

from argparse import ArgumentParser

from testlib import Color, run_shell

GIT_LS_FILES = r"""
git ls-files -c -o --exclude-standard --deduplicate -z -- '**_vars/**vault.'{yaml,yml,json} '*.'{key,csr,p12} \
    '**/'{private,privkey,\*[-.]key}.pem \
    | xargs -0 -r grep --files-without-match -- $'^$ANSIBLE_VAULT' ||:
"""

args_parser = ArgumentParser(
    usage="ansible-vault.py [--help]",
    description="Check sensitive files that must be ansible-vault encrpyted in the repository.",
)


def assert_ansible_vault_files() -> bool:
    if paths := run_shell(GIT_LS_FILES):
        print(*paths, sep="\n", file=sys.stderr)
        return False
    return True


def main() -> None:
    _ = args_parser.parse_args()
    print(f"{Color.CYAN}Running: {Color.BOLD}ansible-vault.py{Color.CLEAR}", file=sys.stderr)

    if assert_ansible_vault_files():
        print(f"{Color.GREEN}ansible-vault files passed.{Color.CLEAR}", file=sys.stderr)
        sys.exit(0)

    print(f"{Color.RED}ansible-vault files failed!{Color.CLEAR}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

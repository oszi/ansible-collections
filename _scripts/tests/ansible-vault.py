#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring

import sys

from argparse import ArgumentParser

from utils import Color, run_shell

GIT_LS_FILES = r"""
git ls-files -c -o --exclude-standard --deduplicate -z -- '**_vars/**vault.'{yaml,yml,json} '*.'{key,csr,p12} \
    '**/'{private,privkey,\*[-.]key}.pem \
    | xargs -0 -r grep --files-without-match -- $'^$ANSIBLE_VAULT' ||:
"""

args_parser = ArgumentParser(
    usage="ansible-vault.py [--help]",
    description="Check sensitive files that must be ansible-vault encrpyted in the repository.",
)


def run_ansible_vault_check() -> int:
    paths = run_shell(GIT_LS_FILES)
    if not paths:
        print(f"{Color.GREEN}ansible-vault files check passed.{Color.CLEAR}", file=sys.stderr)
        return 0

    print(*paths, sep="\n", file=sys.stderr)
    print(f"{Color.RED}Clear-text private keys or vault files!{Color.CLEAR}", file=sys.stderr)
    return 1


def main() -> None:
    _ = args_parser.parse_args()
    rc = run_ansible_vault_check()
    sys.exit(rc)


if __name__ == "__main__":
    main()

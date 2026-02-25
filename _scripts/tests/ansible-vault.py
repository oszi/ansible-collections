#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser

from testlib import boolean_test_decorator, run_shell_get_lines

GIT_LS_FILES = r"""
set -euo pipefail
git ls-files -c -o --exclude-standard --deduplicate -z -- '**_vars/**vault.'{yaml,yml,json} '*.'{key,csr,p12} \
    '**/'{private,privkey,\*[-.]key}.pem \
    | (xargs -0 -r grep --files-without-match -- $'^$ANSIBLE_VAULT' ||:)
"""

args_parser = ArgumentParser(
    usage="ansible-vault.py [--help]",
    description="Check sensitive files that must be ansible-vault encrpyted in the repository.",
)


@boolean_test_decorator("ansible-vault.py")
def assert_ansible_vault_files() -> bool:
    if paths := run_shell_get_lines(GIT_LS_FILES):
        print(*paths, sep="\n", file=sys.stderr)
        return False
    return True


def main() -> None:
    _ = args_parser.parse_args()
    assert_ansible_vault_files()


if __name__ == "__main__":
    main()

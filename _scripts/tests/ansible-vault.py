#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import re

from argparse import ArgumentParser
from pathlib import Path
from typing import NoReturn

from testlib import boolean_test_decorator, error_code, git_ls_files

VAULT_PATHSPECS = (
    "**_vars/**vault.yaml",
    "**_vars/**vault.yml",
    "**_vars/**vault.json",
    "**/private.pem",
    "**/privkey.pem",
    "**/*[-.]key.pem",
    "*.key",
    "*.csr",
    "*.p12",
)

# The whole envelope written by ansible-vault: header, then hex lines only.
VAULT_ENVELOPE = re.compile(
    rb"\$ANSIBLE_VAULT;1\.[1-9];AES256(?:;[^\r\n]+)?\r?\n(?:[0-9a-fA-F]+\r?\n)*[0-9a-fA-F]+(?:\r?\n)*"
)

args_parser = ArgumentParser(
    usage="ansible-vault.py [--help]",
    description="Check sensitive files that must be ansible-vault encrypted in the repository.",
)


def is_vault_encrypted(path: Path | str) -> bool | NoReturn:
    try:
        with open(path, "rb") as f:
            content = f.read()
    except OSError as err:
        error_code(f"ansible-vault.py: cannot read {path}: {err}", sys_exit=True)
    return VAULT_ENVELOPE.fullmatch(content) is not None


@boolean_test_decorator("ansible-vault.py")
def assert_ansible_vault_files() -> bool:
    if paths := [path for path in git_ls_files(VAULT_PATHSPECS) if not is_vault_encrypted(path)]:
        print(*paths, sep="\n", flush=True)
        return False
    return True


def main() -> None:
    _ = args_parser.parse_args()
    assert_ansible_vault_files()


if __name__ == "__main__":
    main()

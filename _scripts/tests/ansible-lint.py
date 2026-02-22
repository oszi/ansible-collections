#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring

import os
import sys

from argparse import ArgumentParser

from utils import run_tests


args_parser = ArgumentParser(
    usage="ansible-lint.py [--help]",
    description="Run ansible-lint in the repository, disabling ansible-vault.",
)


def run_ansible_lint() -> int:
    env = os.environ.copy()
    env.update(dict.fromkeys(("ANSIBLE_ASK_VAULT_PASS", "ANSIBLE_ASK_PASS", "ANSIBLE_BECOME_ASK_PASS"), "False"))

    # Skip vault scripts as nothing needs to be decrypted for linting.
    if os.path.isfile("/etc/hostname"):
        env["ANSIBLE_VAULT_PASSWORD_FILE"] = "/etc/hostname"
        env["ANSIBLE_VAULT_IDENTITY_LIST"] = "/etc/hostname"

    return run_tests(["ansible-lint"], paths=[], env=env)


def main() -> None:
    _ = args_parser.parse_args()
    rc = run_ansible_lint()
    sys.exit(rc)


if __name__ == "__main__":
    main()

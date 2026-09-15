#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import os
import sys

from argparse import ArgumentParser
from tempfile import TemporaryDirectory

from testlib import run_tests

args_parser = ArgumentParser(
    usage="ansible-lint.py [--help]",
    description="Run ansible-lint in the repository, disabling ansible-vault.",
)


def run_ansible_lint() -> int:
    env = os.environ.copy()
    env.update(dict.fromkeys(("ANSIBLE_ASK_VAULT_PASS", "ANSIBLE_ASK_PASS", "ANSIBLE_BECOME_ASK_PASS"), "False"))

    tempdir = TemporaryDirectory(prefix="ansible-lint-")  # pylint: disable=consider-using-with
    vault_dummy = os.path.join(tempdir.name, "vault-password-dummy")
    with open(vault_dummy, "w", encoding="utf-8") as f:
        f.write("dummy")

    # Disable vault scripts as nothing needs to be decrypted for linting.
    env["ANSIBLE_VAULT_PASSWORD_FILE"] = vault_dummy
    env["ANSIBLE_VAULT_IDENTITY_LIST"] = vault_dummy

    # Change ansible temp directory for read-only, agentic environments.
    env.setdefault("ANSIBLE_LOCAL_TEMP", tempdir.name)
    return run_tests(["ansible-lint"], paths=[], env=env)


def main() -> None:
    _ = args_parser.parse_args()
    rc = run_ansible_lint()
    sys.exit(rc)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser

import yaml

from testlib import NAMESPACE_PATH, META_MAIN_PATH, Color, RC, RoleMeta, boolean_test_decorator, print_error

MUTUALLY_EXCLUSIVE_TAGS = {"baselinux", "containers", "thirdparty", "toolbox", "workstation"}
MUTUALLY_EXCLUSIVE_TAGS_STR = f"{Color.BOLD}{', '.join(sorted(MUTUALLY_EXCLUSIVE_TAGS))}{Color.CLEAR}"

args_parser = ArgumentParser(
    usage="galaxy-tags.py [--help]",
    description="Ensure mandatory galaxy tags in the repository.",
)


@boolean_test_decorator("galaxy-tags.py")
def assert_role_tags() -> bool:
    rc = RC.OK
    role_count = 0
    for role_meta in RoleMeta.from_glob():
        role_count += 1
        role_must_have = f"{Color.BOLD}{role_meta.fqcn}{Color.CLEAR} must have"

        try:
            meta = role_meta.load(raise_errors=True)
        except (OSError, yaml.YAMLError):
            print_error(f"{role_must_have} a valid {META_MAIN_PATH} file!")
            rc = RC.ERROR
            continue

        try:
            tags = set(meta["galaxy_info"]["galaxy_tags"])
        except (KeyError, TypeError):
            print_error(f"{role_must_have} galaxy tags, there are none!")
            rc = RC.ERROR
            continue

        if role_meta.collection.name not in tags:
            print_error(f"{role_must_have} the tag: {Color.BOLD}{role_meta.collection.name}{Color.CLEAR}")
            rc = RC.ERROR

        if len(tags.intersection(MUTUALLY_EXCLUSIVE_TAGS)) != 1:
            print_error(f"{role_must_have} one of the tags: {MUTUALLY_EXCLUSIVE_TAGS_STR}")
            rc = RC.ERROR

    if role_count > 0:
        print(f"Asserted tags on {role_count} roles in namespace:{NAMESPACE_PATH.name}.", file=sys.stderr)
    else:
        print(f"No roles in this repository in namespace:{NAMESPACE_PATH.name}.", file=sys.stderr)

    return rc == RC.OK


def main() -> None:
    _ = args_parser.parse_args()
    assert_role_tags()


if __name__ == "__main__":
    main()

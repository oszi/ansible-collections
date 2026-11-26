#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser

import yaml

from testlib import NAMESPACE_PATH, Color, RC, RoleMeta, boolean_test_decorator, chdir_project, print_error

MUTUALLY_EXCLUSIVE_TAGS = {"baselinux", "containers", "thirdparty", "toolbox", "workstation"}
MUTUALLY_EXCLUSIVE_TAGS_STR = Color.BOLD(*sorted(MUTUALLY_EXCLUSIVE_TAGS), sep=", ")

args_parser = ArgumentParser(
    usage="galaxy-tags.py [--help]",
    description="Ensure mandatory galaxy tags in the repository.",
)


@boolean_test_decorator("galaxy-tags.py")
def assert_role_tags() -> bool:
    rc = RC.OK
    role_count = 0
    for role_meta in RoleMeta.all_roles():
        role_count += 1
        role_must_have = f"{Color.BOLD(role_meta.fqcn)} must have"

        try:
            meta = role_meta.load_meta(raise_errors=True)
        except (OSError, ValueError, yaml.YAMLError):
            print_error(f"{role_must_have} a valid {RoleMeta.META_MAIN_PATH} file!")
            rc = RC.ERROR
            continue

        try:
            tags = set(meta["galaxy_info"]["galaxy_tags"])
        except (KeyError, TypeError):
            print_error(f"{role_must_have} galaxy tags, there are none!")
            rc = RC.ERROR
            continue

        if role_meta.collection_dir.name not in tags:
            print_error(f"{role_must_have} the tag: {Color.BOLD(role_meta.collection_dir.name)}")
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
    chdir_project()
    assert_role_tags()


if __name__ == "__main__":
    main()

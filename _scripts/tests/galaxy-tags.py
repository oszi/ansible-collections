#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

import yaml

from testlib import Color, RC, boolean_test_decorator, error_code

# Relative path to skip checking tags in a parent repository.
NAMESPACE_PATH = Path("ansible_collections") / "oszi"
ROLE_META_GLOB = "*/roles/*/meta/main.y*ml"

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

    for meta_path in NAMESPACE_PATH.glob(ROLE_META_GLOB):
        role_count += 1
        role_path = meta_path.parent.parent
        collection_name = role_path.parent.parent.name
        role_fqcn = f"{NAMESPACE_PATH.name}.{collection_name}.{role_path.name}"
        role_must_have = f"{Color.BOLD}{role_fqcn}{Color.CLEAR} must have"

        try:
            with meta_path.open("r", encoding="utf-8") as f:
                meta: Dict[str, Any] = yaml.safe_load(f)
        except (OSError, yaml.YAMLError):
            rc = error_code(f"{role_must_have} a valid meta/main yaml file!")
            continue

        try:
            tags = set(meta["galaxy_info"]["galaxy_tags"])
        except (KeyError, TypeError):
            rc = error_code(f"{role_must_have} galaxy tags, there are none!")
            continue

        if collection_name not in tags:
            rc = error_code(f"{role_must_have} the tag: {Color.BOLD}{collection_name}{Color.CLEAR}")

        if len(tags.intersection(MUTUALLY_EXCLUSIVE_TAGS)) != 1:
            rc = error_code(f"{role_must_have} one of the tags: {MUTUALLY_EXCLUSIVE_TAGS_STR}")

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

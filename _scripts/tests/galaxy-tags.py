#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

import yaml

from testlib import Color, RC, boolean_test_decorator, error_code

GIT_DIR = Path(__file__).parent.parent.parent.resolve()
NAMESPACE_DIR = GIT_DIR / "ansible_collections" / "oszi"
META_GLOB = "*/roles/*/meta/main.y*ml"

MUTUALLY_EXCLUSIVE_TAGS = {"baselinux", "containers", "thirdparty", "toolbox", "workstation"}
MUTUALLY_EXCLUSIVE_TAGS_STR = f"{Color.BOLD}{', '.join(sorted(MUTUALLY_EXCLUSIVE_TAGS))}{Color.CLEAR}"

ACCEPTED_ASSERT_ROOT_PRIVILEGES_DEPENDENCIES = [
    {
        "role": "oszi.utils.assert",
        "vars": {
            "assert_task_msg": "Assert root privileges",
            "assert_that": ["ansible_facts.user_uid | int == 0"],
        },
    },
    {"role": "oszi.environments.baselinux"},
]

args_parser = ArgumentParser(
    usage="galaxy-tags.py [--help]",
    description="Ensure mandatory galaxy tags in the repository.",
)


def assert_root_privileges_dependency(meta: Dict[str, Any]) -> bool:
    if dependencies := meta.get("dependencies"):
        for dependency in dependencies:
            if dependency in ACCEPTED_ASSERT_ROOT_PRIVILEGES_DEPENDENCIES:
                return True
    return False


@boolean_test_decorator("galaxy-tags.py")
def assert_role_tags() -> bool:
    rc = RC.OK
    assert_root_privileges_noted = False

    for meta_path in NAMESPACE_DIR.glob(META_GLOB):
        role_path = meta_path.parent.parent
        collection_name = role_path.parent.parent.name
        role_fqcn = f"{NAMESPACE_DIR.name}.{collection_name}.{role_path.name}"
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

        if ("rootless" not in tags) ^ assert_root_privileges_dependency(meta):
            rc = error_code(f"{role_must_have} the rootless tag, OR assert root privileges!")
            assert_root_privileges_noted = True

    if rc != RC.OK:
        if assert_root_privileges_noted:
            print(f"{Color.YELLOW}Accepted dependencies to assert root privileges:{Color.CLEAR}", file=sys.stderr)
            yaml.dump(ACCEPTED_ASSERT_ROOT_PRIVILEGES_DEPENDENCIES, sys.stderr)

        return False
    return True


def main() -> None:
    _ = args_parser.parse_args()
    assert_role_tags()


if __name__ == "__main__":
    main()

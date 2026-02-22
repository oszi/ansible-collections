#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
import sys

from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Dict

import yaml

from utils import Color

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
    if "dependencies" in meta:
        for dependency in meta["dependencies"]:
            if dependency in ACCEPTED_ASSERT_ROOT_PRIVILEGES_DEPENDENCIES:
                return True
    return False


def assert_role_tags() -> bool:
    errors = []
    assert_root_privileges_noted = False

    for meta_path in NAMESPACE_DIR.glob(META_GLOB):
        role_path = meta_path.parent.parent
        collection_name = role_path.parent.parent.name
        role_fqcn = f"{NAMESPACE_DIR.name}.{collection_name}.{role_path.name}"
        role_must_have = f"{Color.BOLD}{role_fqcn}{Color.CLEAR} must have"

        with meta_path.open("r", encoding="utf-8") as f:
            meta: Dict[str, Any] = yaml.safe_load(f)

        try:
            tags = set(meta["galaxy_info"]["galaxy_tags"])
        except KeyError:
            errors.append(f"{role_must_have} galaxy tags, there are none!")
            continue

        if collection_name not in tags:
            errors.append(f"{role_must_have} the tag: {Color.BOLD}{collection_name}{Color.CLEAR}")

        if len(tags.intersection(MUTUALLY_EXCLUSIVE_TAGS)) != 1:
            errors.append(f"{role_must_have} one of the tags: {MUTUALLY_EXCLUSIVE_TAGS_STR}")

        if "rootless" not in tags and not assert_root_privileges_dependency(meta):
            errors.append(f"{role_must_have} the rootless tag or assert root privileges")
            assert_root_privileges_noted = True

    if not errors:
        print(f"{Color.GREEN}galaxy-tags check passed.{Color.CLEAR}", file=sys.stderr)
        return True

    print(*errors, sep="\n", file=sys.stderr)
    if assert_root_privileges_noted:
        print(f"{Color.YELLOW}Accepted dependencies to assert root privileges:{Color.CLEAR}", file=sys.stderr)
        yaml.dump(ACCEPTED_ASSERT_ROOT_PRIVILEGES_DEPENDENCIES, sys.stderr)

    print(f"{Color.RED}galaxy-tags check failed!{Color.CLEAR}", file=sys.stderr)
    return False


def main() -> None:
    _ = args_parser.parse_args()
    res = assert_role_tags()
    sys.exit(0 if res else 1)


if __name__ == "__main__":
    main()

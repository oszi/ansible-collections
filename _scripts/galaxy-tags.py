#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
# This script does not support symlinking into a parent repository - e.g. inventory.
import json
import os
import sys

from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

import yaml

_SCRIPTS_PATH = Path(__file__).resolve().parent

sys.path.insert(0, str(_SCRIPTS_PATH / "tests"))

from testlib import RoleMeta  # pylint: disable=wrong-import-position

args_parser = ArgumentParser(
    usage="galaxy-tags.py [--help] [--json] [--tags=TAG1,TAG2]",
    description="List ansible roles grouped by galaxy tags.",
)

args_parser.add_argument("--json", help="output json instead of yaml", action="store_true", default=False)
args_parser.add_argument("--tags", "-t", help="filter to specific tag(s)")


def get_galaxy_tags(tags_filter: Optional[List[str]] = None) -> Dict[str, List[str]]:
    tags_to_roles: Dict[str, Set[str]] = defaultdict(set)
    for role_meta in RoleMeta.from_glob():
        meta = role_meta.load(raise_errors=False)

        for tag in (meta.get("galaxy_info") or {}).get("galaxy_tags") or []:
            if tags_filter is None or tag in tags_filter:
                tags_to_roles[tag].add(role_meta.fqcn)

    return {key: list(sorted(value)) for key, value in sorted(tags_to_roles.items())}


def main() -> None:
    app_args = args_parser.parse_args()
    tags_filter = [t.strip() for t in app_args.tags.split(",")] if app_args.tags else None

    os.chdir(_SCRIPTS_PATH.parent)
    result = get_galaxy_tags(tags_filter)

    if app_args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        yaml.dump(result, sys.stdout)


if __name__ == "__main__":
    main()

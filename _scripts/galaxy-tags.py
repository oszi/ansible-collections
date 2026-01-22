#!/usr/bin/env python3
# pylint: disable=invalid-name,line-too-long,missing-function-docstring,missing-module-docstring
# black -l 120 --target-version=py311 _scripts/galaxy-tags.py
import json
import sys

from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

import yaml

GIT_DIR = Path(__file__).parent.parent.resolve()
NAMESPACE_DIR = GIT_DIR / "ansible_collections" / "oszi"
META_GLOB = "*/roles/*/meta/main.y*ml"

args_parser = ArgumentParser(
    usage="galaxy-tags.py [--help] [--json] [--tags=TAG1,TAG2]",
    description="List ansible roles grouped by galaxy tags.",
)

args_parser.add_argument("--json", help="output json instead of yaml", action="store_true", default=False)
args_parser.add_argument("--tags", "-t", help="filter to specific tag(s)")


def get_galaxy_tags(tags_filter: Optional[List[str]] = None) -> Dict[str, List[str]]:
    tags_to_roles: Dict[str, Set[str]] = defaultdict(set)

    for meta_path in NAMESPACE_DIR.glob(META_GLOB):
        role_path = meta_path.parent.parent
        role_fqcn = f"{NAMESPACE_DIR.name}.{role_path.parent.parent.name}.{role_path.name}"

        with meta_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)

        for tag in meta["galaxy_info"]["galaxy_tags"]:  # ansible-lint validated
            if tags_filter is None or tag in tags_filter:
                tags_to_roles[tag].add(role_fqcn)

    return {key: list(sorted(value)) for key, value in sorted(tags_to_roles.items())}


def main():
    app_args = args_parser.parse_args()
    tags_filter = [t.strip() for t in app_args.tags.split(",")] if app_args.tags else None
    result = get_galaxy_tags(tags_filter)

    if app_args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        yaml.dump(result, sys.stdout)


if __name__ == "__main__":
    main()

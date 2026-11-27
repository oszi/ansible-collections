# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import re

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .console import print_warning

__all__ = [
    "COLLECTIONS",
    "NAMESPACE_PATH",
    "ProjectPath",
    "ProjectRoleMeta",
]

COLLECTIONS = ("environments", "general", "thirdparty", "utils")
NAMESPACE_PATH = Path("ansible_collections") / "oszi"


# Lexical: collection and role properties expect paths relative to the project root, e.g. via relative_to_cwd().
class ProjectPath(Path):
    # Allow names that are likely not false-positives; ansible-lint validates strict naming.
    ROLE_NAME_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*")
    ROLES_GLOB = "roles/[a-zA-Z]*/"

    @property
    def collection_dir(self) -> Optional["ProjectPath"]:
        if (path := self.child_base_of(NAMESPACE_PATH)) and path.name in COLLECTIONS:
            return path
        return None

    @property
    def collection_fqcn(self) -> Optional[str]:
        if collection_dir := self.collection_dir:
            parts = collection_dir.parts
            return f"{parts[-2]}.{parts[-1]}"
        return None

    @property
    def collection_role_dir(self) -> Optional["ProjectPath"]:
        if (collection_dir := self.collection_dir) and (path := self.child_base_of(collection_dir / "roles")):
            if self.ROLE_NAME_RE.fullmatch(path.name) is not None:
                return path
        return None

    @property
    def collection_role_fqcn(self) -> Optional[str]:
        if role_dir := self.collection_role_dir:
            parts = role_dir.parts
            return f"{parts[-4]}.{parts[-3]}.{parts[-1]}"
        return None

    def child_base_of(self, base: Path) -> Optional["ProjectPath"]:
        parts, base_parts = self.parts, base.parts
        base_len = len(base_parts)
        if len(parts) > base_len and parts[:base_len] == base_parts:
            return type(self)(*parts[: base_len + 1])
        return None

    def lexical_absolute(self) -> "ProjectPath":
        return type(self)(os.path.abspath(self))

    def relative_to_cwd(self) -> "ProjectPath":
        # Rebase onto the shallowest ancestor that is the current directory, also via a symlinked prefix,
        # and keep the rest lexical, so symlinks below it, e.g. a symlinked collection, are never followed out.
        absolute = self.lexical_absolute()
        cwd = Path.cwd()
        for ancestor in reversed((absolute, *absolute.parents)):
            try:
                if ancestor == cwd or os.path.samefile(ancestor, cwd):
                    return absolute.relative_to(ancestor)
            except OSError:
                continue
        return absolute

    @classmethod
    def all_collections(cls) -> List["ProjectPath"]:
        return [cls(path) for collection in COLLECTIONS if (path := NAMESPACE_PATH / collection).is_dir()]

    @classmethod
    def all_collection_roles(cls) -> List["ProjectPath"]:
        return [
            role_dir
            for collection_dir in cls.all_collections()
            for role_dir in sorted(collection_dir.glob(cls.ROLES_GLOB))
            if cls.ROLE_NAME_RE.fullmatch(role_dir.name) is not None
        ]


class ProjectRoleMeta:
    # Enforce meta/main.yml as the only accepted format.
    META_MAIN_PATH = Path("meta") / "main.yml"

    def __init__(self, *args: Path | str):
        self.role_dir = ProjectPath(*args)
        if self.role_dir.collection_role_dir != self.role_dir:
            raise ValueError(f"{self.role_dir} is not a role path in {NAMESPACE_PATH}")

    @property
    def collection_dir(self) -> ProjectPath:  # Never None.
        return self.role_dir.collection_dir

    @property
    def fqcn(self) -> str:  # Never None.
        return self.role_dir.collection_role_fqcn

    @property
    def meta_path(self) -> ProjectPath:
        return self.role_dir / self.META_MAIN_PATH

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.role_dir!r})"

    def __str__(self) -> str:
        return str(self.meta_path)

    def load_meta(self, raise_errors: bool = True) -> Dict[str, Any]:
        try:
            with self.meta_path.open("r", encoding="utf-8") as f:
                meta = yaml.safe_load(f)
            if not isinstance(meta, dict):
                raise ValueError("yaml is not a mapping")
            return meta
        except (OSError, ValueError, yaml.YAMLError) as err:
            if raise_errors:
                raise
            print_warning(f"{self.fqcn}: {err}")
        return {}

    def load_dependencies(self) -> Set[str]:
        dependencies = self.load_meta(raise_errors=False).get("dependencies") or []
        return {
            entry.get("role", entry.get("name", "")) if isinstance(entry, dict) else str(entry)
            for entry in dependencies
        }

    def load_galaxy_tags(self) -> List[str]:
        galaxy_info = self.load_meta(raise_errors=False).get("galaxy_info") or {}
        return galaxy_info.get("galaxy_tags") or []

    @classmethod
    def all_collection_roles(cls) -> List["ProjectRoleMeta"]:
        return [cls(role_dir) for role_dir in ProjectPath.all_collection_roles()]

    @classmethod
    def from_fqcn(cls, fqcn: str) -> "ProjectRoleMeta":
        parts = fqcn.split(".")
        if len(parts) != 3:
            raise ValueError(f"FQCN: {fqcn} is not of 3 parts!")
        if parts[0] != NAMESPACE_PATH.name:
            raise ValueError(f"FQCN: {fqcn} is not in namespace:{NAMESPACE_PATH.name}!")
        if parts[1] not in COLLECTIONS:
            raise ValueError(f"FQCN: {fqcn} is not in a collection of {', '.join(COLLECTIONS)}!")
        return cls(NAMESPACE_PATH, parts[1], "roles", parts[2])

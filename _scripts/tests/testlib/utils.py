# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import re
import subprocess as sp
import sys

from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, IO, List, NoReturn, Optional, Set, Tuple

import yaml

__all__ = [
    "COLLECTIONS",
    "NAMESPACE_PATH",
    "ANSIBLE_NO_PROMPT_ENV",
    "ANSIBLE_ROLE_NAME_RE",
    "ANSIBLE_ROLES_GLOB",
    "getenv_bool",
    "io_is_tty",
    "split_passthrough_args",
    "Color",
    "Output",
    "RC",
    "ProjectPath",
    "RoleMeta",
]

COLLECTIONS = ("environments", "general", "thirdparty", "utils")
NAMESPACE_PATH = Path("ansible_collections") / "oszi"

ANSIBLE_NO_PROMPT_ENV = {
    "ANSIBLE_ASK_PASS": "False",
    "ANSIBLE_ASK_VAULT_PASS": "False",
    "ANSIBLE_BECOME_ASK_PASS": "False",
}

ANSIBLE_ROLE_NAME_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]*")
ANSIBLE_ROLES_GLOB = "roles/[a-zA-Z]*/"


def getenv_bool(key: str, default: bool = False) -> bool:
    if key not in os.environ:
        return default
    return os.environ[key].lower() in {"true", "yes", "y", "1"}


def io_is_tty(io: IO | Any) -> bool:
    try:
        return os.isatty(io.fileno())
    except (AttributeError, OSError):
        return False


def split_passthrough_args(argv: List[str], keep_separator: bool = False) -> Tuple[List[str], List[str]]:
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index if keep_separator else index + 1 :]
    return argv, []


class Color:
    COLORS_ENABLED = getenv_bool(
        "TESTLIB_COLORS_ENABLED", not getenv_bool("NO_COLOR") and (getenv_bool("PY_COLORS") or io_is_tty(sys.stderr))
    )

    @staticmethod
    def sgr(code: int) -> str:
        return f"\033[{code}m" if Color.COLORS_ENABLED else ""

    class ColorCode:
        def __init__(self, code: int, reset: int = 0):
            self.code = code
            self.reset = reset

        def __call__(self, *values: Any, sep: str = " ") -> str:
            return f"{Color.sgr(self.code)}{sep.join(map(str, values))}{Color.sgr(self.reset)}"

        def __repr__(self) -> str:
            return f"{self.__class__.__qualname__}({self.code!r}, {self.reset!r})"

        def __str__(self) -> str:
            return Color.sgr(self.code)

        def __invert__(self) -> "Color.ColorCode":
            return Color.ColorCode(self.reset, self.code)

    CLEAR = ColorCode(0, 0)
    BOLD = ColorCode(1, 22)
    HIGHLIGHT = ColorCode(7, 27)
    RED = ColorCode(31, 39)
    GREEN = ColorCode(32, 39)
    YELLOW = ColorCode(33, 39)
    BLUE = ColorCode(34, 39)
    MAGENTA = ColorCode(35, 39)
    CYAN = ColorCode(36, 39)


class Output(StrEnum):
    LIVE_WITH_STATUS = "live_with_status"
    LIVE_QUIET = "live_quiet"
    BUFFERED_WITH_STATUS = "buffered_with_status"
    BUFFERED_QUIET = "buffered_quiet"
    ON_FAILURE_WITH_STATUS = "on_failure_with_status"
    ON_FAILURE_QUIET = "on_failure_quiet"
    DISCARD = "discard"

    @property
    def is_on_failure(self) -> bool:
        return self in (Output.ON_FAILURE_WITH_STATUS, Output.ON_FAILURE_QUIET)

    @property
    def is_buffered(self) -> bool:
        return self in (Output.BUFFERED_WITH_STATUS, Output.BUFFERED_QUIET) or self.is_on_failure

    @property
    def has_status(self) -> bool:
        return self in (Output.LIVE_WITH_STATUS, Output.BUFFERED_WITH_STATUS, Output.ON_FAILURE_WITH_STATUS)

    @property
    def stdout(self) -> Optional[int]:
        return sp.DEVNULL if self == Output.DISCARD else sp.PIPE if self.is_buffered else None

    @property
    def stderr(self) -> Optional[int]:
        # If not live, redirect stderr to stdout to preserve ordering.
        return sp.STDOUT if self.stdout is not None else None


class RC:
    OK = 0
    ERROR = 1
    TIMEOUT = 124
    SIGNAL_BASE = 128
    SIGNAL_MAX = SIGNAL_BASE + 64
    INTERRUPT = SIGNAL_BASE + 2  # SIGINT
    RC_MAX = 255

    @staticmethod
    def is_signal(rc: int) -> bool:
        return rc < 0 or RC.SIGNAL_BASE < rc <= RC.SIGNAL_MAX

    @staticmethod
    def is_early_exit(rc: int) -> bool:
        return RC.is_signal(rc) or rc == RC.TIMEOUT

    @staticmethod
    def status(rc: int, sys_exit: bool = False) -> int | NoReturn:
        if not isinstance(rc, int):
            raise TypeError("RC.status called with non-integer rc")

        if rc < 0:
            rc = min(RC.SIGNAL_BASE - rc, RC.SIGNAL_MAX)
        rc = min(rc, RC.RC_MAX)

        if sys_exit:
            sys.exit(rc)
        return rc

    @staticmethod
    def select(*args: int, sys_exit: bool = False) -> int | NoReturn:
        rc = RC.OK
        for arg in args:
            if RC.is_signal(arg):
                rc = arg
                break
            if rc == RC.OK:
                rc = arg

        return RC.status(rc, sys_exit)


class ProjectPath(Path):
    # Lexical: collection and role properties expect paths relative to the project root, e.g. via relative_to_cwd().

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
    def role_dir(self) -> Optional["ProjectPath"]:
        if (collection_dir := self.collection_dir) and (path := self.child_base_of(collection_dir / "roles")):
            if ANSIBLE_ROLE_NAME_RE.fullmatch(path.name) is not None:
                return path
        return None

    @property
    def role_fqcn(self) -> Optional[str]:
        if role_dir := self.role_dir:
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


class RoleMeta:
    # Enforce meta/main.yml as the only accepted format.
    META_MAIN_PATH = Path("meta") / "main.yml"

    def __init__(self, *args: Path | str):
        self.role_dir = ProjectPath(*args)
        if self.role_dir.role_dir != self.role_dir:
            raise ValueError(f"{self} is not a role path in {NAMESPACE_PATH}")

    @property
    def collection_dir(self) -> ProjectPath:
        return self.role_dir.collection_dir

    @property
    def meta_path(self) -> Path:
        return self.role_dir / RoleMeta.META_MAIN_PATH

    @property
    def fqcn(self) -> str:
        return self.role_dir.role_fqcn

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.role_dir!r})"

    def __str__(self) -> str:
        return str(self.role_dir)

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
            print(Color.YELLOW(f"WARNING: {self.fqcn}: {err}"), file=sys.stderr)
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
    def all_roles(cls) -> List["RoleMeta"]:
        return [
            cls(role_dir)
            for collection_dir in ProjectPath.all_collections()
            for role_dir in sorted(collection_dir.glob(ANSIBLE_ROLES_GLOB))
            if ANSIBLE_ROLE_NAME_RE.fullmatch(role_dir.name) is not None
        ]

    @classmethod
    def from_fqcn(cls, fqcn: str) -> "RoleMeta":
        parts = fqcn.split(".")
        if len(parts) != 3:
            raise ValueError(f"FQCN: {fqcn} is not of 3 parts!")
        if parts[0] != NAMESPACE_PATH.name:
            raise ValueError(f"FQCN: {fqcn} is not in namespace:{NAMESPACE_PATH.name}!")
        if parts[1] not in COLLECTIONS:
            raise ValueError(f"FQCN: {fqcn} is not in a collection of {', '.join(COLLECTIONS)}!")
        return cls(NAMESPACE_PATH, parts[1], "roles", parts[2])

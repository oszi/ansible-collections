# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import subprocess as sp
import sys

from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, IO, List, NoReturn, Optional, Tuple

import yaml

__all__ = [
    "COLLECTIONS",
    "NAMESPACE_PATH",
    "all_collection_paths",
    "getenv_bool",
    "io_is_tty",
    "split_passthrough_args",
    "Color",
    "Output",
    "RC",
    "RoleMeta",
]

COLLECTIONS = ("environments", "general", "thirdparty", "utils")
NAMESPACE_PATH = Path("ansible_collections") / "oszi"


def all_collection_paths() -> List[Path]:
    return [NAMESPACE_PATH / collection for collection in COLLECTIONS]


def getenv_bool(key: str, default: bool = False) -> bool:
    if key not in os.environ:
        return default
    return os.environ[key].lower() in {"true", "yes", "y", "1"}


def io_is_tty(io: IO | Any) -> bool:
    try:
        return os.isatty(io.fileno())
    except (AttributeError, OSError):
        return False


def split_passthrough_args(argv: List[str]) -> Tuple[List[str], List[str]]:
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index + 1 :]
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

        def __call__(self, text: Any) -> str:
            return f"{Color.sgr(self.code)}{text}{Color.sgr(self.reset)}"

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


class RoleMeta:
    # Enforce meta/main.yml as the only accepted format.
    META_MAIN_PATH = Path("meta") / "main.yml"

    def __init__(self, role_path: Path | str):
        self.meta_path = Path(role_path) / RoleMeta.META_MAIN_PATH

    @property
    def role(self) -> Path:
        return self.meta_path.parent.parent

    @property
    def collection(self) -> Path:
        return self.role.parent.parent

    @property
    def namespace(self) -> Path:
        return self.collection.parent

    @property
    def fqcn(self) -> str:
        return f"{self.namespace.name}.{self.collection.name}.{self.role.name}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.role!r})"

    def __str__(self) -> str:
        return str(self.meta_path)

    def load(self, raise_errors: bool = True) -> Dict[str, Any]:
        try:
            with self.meta_path.open("r", encoding="utf-8") as f:
                meta = yaml.safe_load(f)
            if not isinstance(meta, dict):
                raise ValueError("yaml is not a mapping")
            return meta
        except (OSError, ValueError, yaml.YAMLError) as err:
            if raise_errors:
                raise
            print(Color.YELLOW(f"WARNING: Failed to load {self.meta_path}: {err}"), file=sys.stderr)
        return {}

    @staticmethod
    def from_glob(collection: Optional[str] = None) -> List["RoleMeta"]:
        pattern = f"{collection or '[a-zA-Z]*'}/roles/[a-zA-Z]*/"
        return [RoleMeta(role_path) for role_path in sorted(NAMESPACE_PATH.glob(pattern))]

    @staticmethod
    def from_fqcn(fqcn: str) -> "RoleMeta":
        parts = fqcn.split(".")
        if len(parts) != 3:
            raise ValueError(f"{fqcn} is not of 3 parts!")
        if parts[0] != NAMESPACE_PATH.name:
            raise ValueError(f"{fqcn} is not in namespace:{NAMESPACE_PATH.name}!")
        return RoleMeta(NAMESPACE_PATH / parts[1] / "roles" / parts[2])

# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import subprocess as sp
import sys
import time

from enum import StrEnum
from typing import Any, IO, List, NoReturn, Optional, Tuple

__all__ = [
    "DEBUG",
    "DEBUG_HELP",
    "Color",
    "OutputMode",
    "RC",
    "getenv_bool",
    "io_is_tty",
    "print_error",
    "print_warning",
    "print_hint",
    "print_success",
    "print_test_cmd",
    "split_passthrough_args",
]


def getenv_bool(key: str, default: bool = False) -> bool:
    if key not in os.environ:
        return default
    return os.environ[key].lower() in {"true", "yes", "y", "1"}


def io_is_tty(io: IO | Any) -> bool:
    try:
        return os.isatty(io.fileno())
    except (AttributeError, OSError):
        return False


DEBUG = getenv_bool("TESTLIB_DEBUG")
DEBUG_HELP = "Set env TESTLIB_DEBUG=True for traceback."


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


class OutputMode(StrEnum):
    LIVE_WITH_STATUS = "live_with_status"
    LIVE_QUIET = "live_quiet"
    BUFFERED_WITH_STATUS = "buffered_with_status"
    BUFFERED_QUIET = "buffered_quiet"
    ON_FAILURE_WITH_STATUS = "on_failure_with_status"
    ON_FAILURE_QUIET = "on_failure_quiet"
    DISCARD = "discard"

    @property
    def is_on_failure(self) -> bool:
        return self in (OutputMode.ON_FAILURE_WITH_STATUS, OutputMode.ON_FAILURE_QUIET)

    @property
    def is_buffered(self) -> bool:
        return self in (OutputMode.BUFFERED_WITH_STATUS, OutputMode.BUFFERED_QUIET) or self.is_on_failure

    @property
    def has_status(self) -> bool:
        return self in (OutputMode.LIVE_WITH_STATUS, OutputMode.BUFFERED_WITH_STATUS, OutputMode.ON_FAILURE_WITH_STATUS)

    @property
    def stdout(self) -> Optional[int]:
        return sp.DEVNULL if self == OutputMode.DISCARD else sp.PIPE if self.is_buffered else None

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


def print_error(message: str, rc: int = RC.ERROR) -> None:
    if RC.is_early_exit(rc):
        color = Color.MAGENTA
    else:
        color = Color.RED

    print(color(message), file=sys.stderr)


def print_warning(message: str) -> None:
    print(Color.YELLOW(f"WARNING: {message}"), file=sys.stderr)


def print_hint(message: str, *lines: Any, line_sep: str = "\n# ") -> None:
    print(Color.BLUE(f"HINT: {message}", *lines, sep=line_sep), file=sys.stderr)


def print_success(message: str) -> None:
    print(Color.GREEN(message), file=sys.stderr)


def print_test_cmd(cmd: List[str], targets: Optional[List[Any]] = None, cwd: Optional[str] = None) -> None:
    message = Color.CYAN("Running:", Color.BOLD(*cmd))
    if cwd:
        message += f" @{cwd}"
    if targets:
        message += f" # {len(targets)} target(s)"
    if DEBUG:
        message += f" # at {time.strftime('%H:%M:%S')}"

    print(message, file=sys.stderr)


def split_passthrough_args(argv: List[str], keep_separator: bool = False) -> Tuple[List[str], List[str]]:
    if "--" in argv:
        index = argv.index("--")
        return argv[:index], argv[index if keep_separator else index + 1 :]
    return argv, []

# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import functools
import os
import subprocess as sp
import sys
import threading
import time
import traceback

from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
from typing import Any, Callable, Dict, IO, List, NoReturn, Optional, ParamSpec

assert sys.version_info >= (3, 11)

# Override /bin/sh for bash on Debian/Ubuntu.
SHELL = "/bin/bash"

OUTPUT_LOCK = threading.Lock()


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
        "TESTLIB_COLORS_ENABLED", not getenv_bool("NO_COLOR") and (getenv_bool("PY_COLORS") or io_is_tty(sys.stdout))
    )

    class ColorCode:
        def __init__(self, code: int):
            self.code = code

        def __str__(self) -> str:
            return f"\033[{self.code}m" if Color.COLORS_ENABLED else ""

    CLEAR = ColorCode(0)
    BOLD = ColorCode(1)
    HIGHLIGHT = ColorCode(7)
    RED = ColorCode(31)
    GREEN = ColorCode(32)
    YELLOW = ColorCode(33)
    BLUE = ColorCode(34)
    MAGENTA = ColorCode(35)
    CYAN = ColorCode(36)


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


def print_error(message: str, rc: int = RC.ERROR) -> None:
    if RC.is_early_exit(rc):
        color = Color.MAGENTA
    else:
        color = Color.RED

    print(f"{color}{message}{Color.CLEAR}", file=sys.stderr)


def print_warning(message: str) -> None:
    print(f"{Color.YELLOW}WARNING: {message}{Color.CLEAR}", file=sys.stderr)


def print_hint(message: str) -> None:
    print(f"{Color.BLUE}HINT: {message}{Color.CLEAR}", file=sys.stderr)


def print_success(message: str) -> None:
    print(f"{Color.GREEN}{message}{Color.CLEAR}", file=sys.stderr)


def print_test_cmd(cmd: List[str], targets: Optional[List[str]] = None, cwd: Optional[str] = None) -> None:
    message = f"{Color.CYAN}Running: {Color.BOLD}{' '.join(cmd)}{Color.CLEAR}"
    if cwd:
        message += f" @{cwd}"
    if targets:
        message += f" # {len(targets)} target(s)"
    if DEBUG:
        message += f" # at {time.strftime('%H:%M:%S')}"

    print(message, file=sys.stderr)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        duration = f"{seconds:.2f}s"
    else:
        minutes, seconds_mod = divmod(round(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        duration = f"{hours}h {minutes}m {seconds_mod}s" if hours else f"{minutes}m {seconds_mod}s"

    if DEBUG:
        duration += f" at {time.strftime('%H:%M:%S')}"
    return duration


def error_code(message: str, rc: int = RC.ERROR, sys_exit: bool = False) -> int | NoReturn:
    if not isinstance(rc, int):
        raise TypeError("testlib.error_code called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.error_code called with RC.OK")

    print_error(message, rc)
    return RC.status(rc, sys_exit)


def error_code_exc(
    subject: str, err: BaseException, duration: Optional[float] = None, sys_exit: bool = False
) -> int | NoReturn:
    duration_str = f" after {format_duration(duration)}" if duration is not None else ""
    if isinstance(err, KeyboardInterrupt):
        message = f"{subject} was interrupted{duration_str}!"
        rc = RC.INTERRUPT
    elif isinstance(err, sp.TimeoutExpired):
        message = f"{subject} has timed out{duration_str}!"
        rc = RC.TIMEOUT
    elif isinstance(err, sp.CalledProcessError):
        message = f"{subject} failed{duration_str}!"
        rc = err.returncode
    else:
        message = f"{subject} failed{duration_str}: {err}"
        rc = RC.ERROR

    if DEBUG:
        traceback.print_exception(err)
    elif not RC.is_early_exit(rc):
        print_hint(DEBUG_HELP)

    return error_code(message, rc, sys_exit)


def failure(
    subject: str, rc: int = RC.ERROR, duration: Optional[float] = None, sys_exit: bool = False
) -> int | NoReturn:
    if not isinstance(rc, int):
        raise TypeError("testlib.failure called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.failure called with RC.OK")

    duration_str = f" after {format_duration(duration)}" if duration is not None else ""
    if rc == RC.TIMEOUT:
        message = f"{subject} has timed out{duration_str}!"
    elif RC.is_signal(rc):
        message = f"{subject} was interrupted{duration_str}!"
    else:
        message = f"{subject} failed{duration_str}!"

    return error_code(message, rc, sys_exit)


def success(subject: str, duration: Optional[float] = None, sys_exit: bool = False) -> int | NoReturn:
    duration_str = f" in {format_duration(duration)}" if duration is not None else ""
    print_success(f"{subject} passed{duration_str}!")
    return RC.status(RC.OK, sys_exit)


def run_shell_get_lines(shell_cmd: str, unique: bool = False, **kwargs) -> List[str]:
    try:
        lines = sp.check_output(
            shell_cmd, executable=SHELL, shell=True, encoding="utf-8", errors="surrogateescape", **kwargs
        ).splitlines()
    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        error_code_exc("testlib.run_shell_get_lines", err, sys_exit=True)

    if unique:
        lines = list(dict.fromkeys(lines))
    return lines


def run_test_cmd(  # pylint: disable=too-many-arguments
    cmd: List[str],
    targets: List[str],
    subject: str,
    *,
    timeout: Optional[float] = None,
    output: Output = Output.LIVE_WITH_STATUS,
    **kwargs,
) -> int | NoReturn:
    if not isinstance(cmd, list):
        raise TypeError("run_test_cmd: cmd is not a list")
    if not isinstance(targets, list):
        raise TypeError("run_test_cmd: targets is not a list")

    if output.has_status:
        with OUTPUT_LOCK:
            print_test_cmd(cmd, targets, kwargs.get("cwd"))

    start = time.monotonic()
    try:
        result = sp.run(
            cmd + targets, check=False, timeout=timeout, stdout=output.stdout, stderr=output.stderr, **kwargs
        )
    except sp.TimeoutExpired as err:
        duration = time.monotonic() - start
        with OUTPUT_LOCK:
            if err.stdout is not None:
                sys.stdout.buffer.write(err.stdout)
                sys.stdout.buffer.flush()
            return error_code_exc(subject, err, duration)

    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        duration = time.monotonic() - start
        with OUTPUT_LOCK:
            return error_code_exc(subject, err, duration)

    duration = time.monotonic() - start
    with OUTPUT_LOCK:
        if result.stdout is not None and (not output.is_on_failure or result.returncode != RC.OK):
            sys.stdout.buffer.write(result.stdout)
            sys.stdout.buffer.flush()

        if result.returncode == RC.OK:
            return success(subject, duration) if output.has_status else RC.OK
        return failure(subject, result.returncode, duration)


def run_tests(cmd: List[str], targets: List[str], *, sys_exit: bool = False, **kwargs) -> int | NoReturn:
    if not isinstance(cmd, list):
        raise TypeError("run_tests: cmd is not a list")
    if not isinstance(targets, list):
        raise TypeError("run_tests: targets is not a list")

    rc = run_test_cmd(cmd, targets, cmd[0], **kwargs)
    return RC.status(rc, sys_exit)


def run_tests_parallel(
    cmd: List[str],
    targets: List[str | Dict[str, Any]],
    *,
    max_workers: Optional[int] = None,
    sys_exit: bool = False,
    **kwargs,
) -> int | NoReturn:
    if not isinstance(cmd, list):
        raise TypeError("run_tests_parallel: cmd is not a list")
    if not isinstance(targets, list):
        raise TypeError("run_tests_parallel: targets is not a list")
    if not targets:
        return run_tests(cmd, targets, sys_exit=sys_exit, **kwargs)
    if "output" not in kwargs:
        kwargs["output"] = Output.BUFFERED_WITH_STATUS

    def run_test_job(target: str | Dict[str, Any]) -> int:
        if isinstance(target, dict):
            job_kwargs = kwargs.copy()
            job_kwargs.update(target)
            job_args = job_kwargs.pop("args", [])
            job_subject = f"{cmd[0]}: {' '.join(job_args) or '-'}"
        else:
            job_kwargs = kwargs
            job_args = [target]
            job_subject = f"{cmd[0]}: {target}"

        return run_test_cmd(cmd + job_args, [], job_subject, **job_kwargs)

    print_test_cmd(cmd, targets, kwargs.get("cwd"))
    sys.stdout.flush()
    sys.stderr.flush()

    rc = RC.OK
    start = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(run_test_job, targets):
                rc = RC.select(rc, result)
    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        duration = time.monotonic() - start
        return error_code_exc(cmd[0], err, duration, sys_exit)

    duration = time.monotonic() - start
    if rc == RC.OK:
        return success(cmd[0], duration, sys_exit)
    return failure(cmd[0], rc, duration, sys_exit)


_PARAMS = ParamSpec("_PARAMS")


def boolean_test_decorator(subject: str) -> Callable[[Callable[_PARAMS, bool]], Callable[_PARAMS, NoReturn]]:
    def inner_decorator(func: Callable[_PARAMS, bool]) -> Callable[_PARAMS, NoReturn]:
        @functools.wraps(func)
        def inner_function(*args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> NoReturn:  # pylint: disable=no-member
            print_test_cmd([subject])
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)

            except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
                duration = time.monotonic() - start
                print_warning(f"Unhandled {err.__class__.__name__}. Beware of zombies.")
                error_code_exc(subject, err, duration, sys_exit=True)

            duration = time.monotonic() - start
            if result is True:
                success(subject, duration, sys_exit=True)
            failure(subject, RC.ERROR, duration, sys_exit=True)

        return inner_function

    return inner_decorator

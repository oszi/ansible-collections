# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import functools
import os
import subprocess as sp
import sys
import threading
import traceback

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, IO, List, NoReturn, Optional, ParamSpec

assert sys.version_info >= (3, 11)

# Override /bin/sh for bash on Debian/Ubuntu.
SHELL = "/bin/bash"


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


def print_test_cmd(cmd: List[str], targets: Optional[List[str]] = None, cwd: Optional[str] = None) -> None:
    message = f"{Color.CYAN}Running test: {Color.BOLD}{' '.join(cmd)}{Color.CLEAR}"
    if cwd:
        message += f" @{cwd}"
    if targets:
        message += f" # {len(targets)} target(s)"

    print(message, file=sys.stderr)


def error_code(message: str, rc: int = RC.ERROR, sys_exit: bool = False) -> int | NoReturn:
    if not isinstance(rc, int):
        raise TypeError("testlib.error_code called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.error_code called with RC.OK")

    print_error(message, rc)
    return RC.status(rc, sys_exit)


def error_code_exc(subject: str, err: BaseException, sys_exit: bool = False) -> int | NoReturn:
    if isinstance(err, KeyboardInterrupt):
        message = f"{subject} was interrupted!"
        rc = RC.INTERRUPT
    elif isinstance(err, sp.TimeoutExpired):
        message = f"{subject} has timed out!"
        rc = RC.TIMEOUT
    elif isinstance(err, sp.CalledProcessError):
        message = f"{subject} failed!"
        rc = err.returncode
    else:
        message = f"{subject} failed: {err}"
        rc = RC.ERROR

    if DEBUG:
        traceback.print_exception(err)
    elif not RC.is_early_exit(rc):
        print_hint(DEBUG_HELP)

    return error_code(message, rc, sys_exit)


def failure(subject: str, rc: int = RC.ERROR, sys_exit: bool = False) -> int | NoReturn:
    if not isinstance(rc, int):
        raise TypeError("testlib.failure called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.failure called with RC.OK")

    if rc == RC.TIMEOUT:
        message = f"{subject} has timed out!"
    elif RC.is_signal(rc):
        message = f"{subject} was interrupted!"
    else:
        message = f"{subject} failed!"

    return error_code(message, rc, sys_exit)


def success(subject: str, sys_exit: bool = False) -> int | NoReturn:
    print(f"{Color.GREEN}{subject} passed!{Color.CLEAR}", file=sys.stderr)
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


output_lock = threading.Lock()


def run_test_cmd(  # pylint: disable=too-many-arguments
    cmd: List[str],
    targets: List[str],
    subject: str,
    *,
    timeout: Optional[float] = None,
    buffered_output: bool = False,
    quiet: bool = False,
    quiet_if_ok: bool = False,
    quiet_success: bool = False,
    **kwargs,
) -> int | NoReturn:
    if not isinstance(cmd, list):
        raise TypeError("run_test_cmd: cmd is not a list")
    if not isinstance(targets, list):
        raise TypeError("run_test_cmd: targets is not a list")

    stdout = sp.DEVNULL if quiet else sp.PIPE if buffered_output or quiet_if_ok else None
    stderr = sp.STDOUT if stdout is not None else None  # Redirect stderr to stdout to preserve ordering.

    try:
        result = sp.run(cmd + targets, timeout=timeout, stdout=stdout, stderr=stderr, check=False, **kwargs)
    except sp.TimeoutExpired as err:
        with output_lock:
            if err.stdout is not None:
                sys.stdout.buffer.write(err.stdout)
                sys.stdout.buffer.flush()
            return error_code_exc(subject, err)

    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        with output_lock:
            return error_code_exc(subject, err)

    with output_lock:
        if result.stdout is not None and (not quiet_if_ok or result.returncode != RC.OK):
            sys.stdout.buffer.write(result.stdout)
            sys.stdout.buffer.flush()

        if result.returncode == RC.OK:
            return success(subject) if not quiet_success else RC.OK
        return failure(subject, result.returncode)


def run_tests(
    cmd: List[str],
    targets: List[str],
    *,
    sys_exit: bool = False,
    **kwargs,
) -> int | NoReturn:
    if not isinstance(cmd, list):
        raise TypeError("run_tests: cmd is not a list")
    if not isinstance(targets, list):
        raise TypeError("run_tests: targets is not a list")

    print_test_cmd(cmd, targets, kwargs.get("cwd"))
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

    if max_workers != 1 and len(targets) > 1:
        kwargs["buffered_output"] = True

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

        if cwd := job_kwargs.get("cwd"):
            job_subject = f"{job_subject} @{cwd}"
        return run_test_cmd(cmd, job_args, job_subject, **job_kwargs)

    print_test_cmd(cmd, targets, kwargs.get("cwd"))
    sys.stdout.flush()
    sys.stderr.flush()

    rc = RC.OK
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(run_test_job, targets):
                rc = RC.select(rc, result)
    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        return error_code_exc(cmd[0], err, sys_exit)

    if rc == RC.OK:
        return success(cmd[0], sys_exit)
    return failure(cmd[0], rc, sys_exit)


_PARAMS = ParamSpec("_PARAMS")


def boolean_test_decorator(subject: str) -> Callable[[Callable[_PARAMS, bool]], Callable[_PARAMS, NoReturn]]:
    def inner_decorator(func: Callable[_PARAMS, bool]) -> Callable[_PARAMS, NoReturn]:
        @functools.wraps(func)
        def inner_function(*args: _PARAMS.args, **kwargs: _PARAMS.kwargs) -> NoReturn:  # pylint: disable=no-member
            print_test_cmd([subject])
            try:
                result = func(*args, **kwargs)

            except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
                print_warning(f"Unhandled {err.__class__.__name__}. Beware of zombies.")
                error_code_exc(subject, err, sys_exit=True)

            if result is True:
                success(subject, sys_exit=True)
            failure(subject, sys_exit=True)

        return inner_function

    return inner_decorator

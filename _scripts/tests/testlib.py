# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import functools
import os
import subprocess as sp
import sys
import traceback

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, IO, List, NoReturn, Optional, ParamSpec

assert sys.version_info >= (3, 11)

# Override /bin/sh for bash on Debian/Ubuntu.
SHELL = "/bin/bash"


def getenv_bool(key: str, default: bool = False) -> bool:
    if key not in os.environ:
        return default
    return os.environ[key].lower() in {"true", "yes", "1"}


def io_is_tty(io: IO | Any) -> bool:
    try:
        return os.isatty(io.fileno())
    except (AttributeError, OSError):
        return False


DEBUG = getenv_bool("TESTLIB_DEBUG")
DEBUG_HELP = "Set env TESTLIB_DEBUG=True for traceback."


class Color:
    COLORS_ENABLED = getenv_bool("TESTLIB_COLORS_ENABLED", io_is_tty(sys.stdout))

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
    INTERRUPT = 128 + 2  # SIGINT

    @staticmethod
    def is_early_exit(rc: int) -> bool:
        return rc > 128 or rc == RC.TIMEOUT


def success(subject: str) -> int:
    print(f"{Color.GREEN}{subject} passed!{Color.CLEAR}", file=sys.stderr)
    return RC.OK


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


def print_test_cmd(cmd: List[str], paths: Optional[List[str]] = None) -> None:
    message = f"{Color.CYAN}Running test: {Color.BOLD}{' '.join(cmd)}{Color.CLEAR}"
    if paths:
        message += f" # {len(paths)} path(s)"

    print(message, file=sys.stderr)


def error_code(message: str, rc: int = RC.ERROR) -> int:
    if not isinstance(rc, int):
        raise TypeError("testlib.error_code called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.error_code called with RC.OK")

    print_error(message, rc)
    return rc


def error_code_exc(subject: str, err: BaseException) -> int:
    if isinstance(err, KeyboardInterrupt):
        message = f"{subject} was interrupted!"
        rc = RC.INTERRUPT
    elif isinstance(err, sp.TimeoutExpired):
        message = f"{subject} has timed out!"
        rc = RC.TIMEOUT
    elif isinstance(err, sp.CalledProcessError):
        message = f"{subject} failed!"
        rc = err.returncode
    elif isinstance(err, OSError):
        message = f"{subject} failed: {err}"
        rc = err.errno or RC.ERROR
    else:
        message = f"{subject} failed: {err}"
        rc = RC.ERROR

    if DEBUG:
        traceback.print_exception(err)
    elif not RC.is_early_exit(rc):
        print_hint(DEBUG_HELP)

    return error_code(message, rc)


def run_shell_get_lines(shell_cmd: str, unique: bool = False, **kwargs) -> List[str]:
    try:
        lines = sp.check_output(shell_cmd, executable=SHELL, shell=True, encoding="utf-8", **kwargs).splitlines()

    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        sys.exit(error_code_exc("testlib.run_shell_get_lines", err))

    if unique:
        lines = list(dict.fromkeys(lines))
    return lines


def run_tests(cmd: List[str], paths: List[str], timeout: Optional[float] = None, **kwargs) -> int:
    if not isinstance(cmd, list):
        raise TypeError("cmd is not a list")
    if not isinstance(paths, list):
        raise TypeError("paths is not a list")

    print_test_cmd(cmd, paths)
    try:
        with sp.Popen(cmd + paths, **kwargs) as proc:
            try:
                rc = proc.wait(timeout)
                if rc == RC.OK:
                    return success(cmd[0])
                return error_code(f"{cmd[0]} failed!", rc)

            except (sp.TimeoutExpired, KeyboardInterrupt) as err:
                rc = error_code_exc(cmd[0], err)
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except sp.TimeoutExpired:
                    proc.kill()
                return rc

    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        return error_code_exc(cmd[0], err)


def run_tests_parallel(
    cmd: List[str],
    paths: List[str],
    timeout: Optional[float] = None,
    quiet: bool = False,
    max_workers: Optional[int] = None,
    **kwargs,
) -> int:
    if not isinstance(cmd, list):
        raise TypeError("cmd is not a list")
    if not isinstance(paths, list):
        raise TypeError("paths is not a list")
    if not paths:
        return run_tests(cmd, paths, timeout, **kwargs)

    print_test_cmd(cmd, paths)

    def run_test(path: str) -> sp.CompletedProcess[str]:
        output = sp.DEVNULL if quiet else sp.PIPE
        return sp.run(cmd + [path], stdout=output, stderr=output, text=True, timeout=timeout, check=False, **kwargs)

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            try:
                results = list(executor.map(run_test, paths))
            except (sp.TimeoutExpired, KeyboardInterrupt):
                executor.shutdown(wait=True, cancel_futures=True)
                raise

    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        return error_code_exc(cmd[0], err)

    rc = RC.OK
    for result in results:
        if result.returncode != RC.OK:
            rc |= result.returncode
            if quiet:
                # Target path of the subprocess, see print_test_cmd
                print_error(result.args[-1])

        if not quiet:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()
            sys.stderr.write(result.stderr)
            sys.stderr.flush()

    if rc == RC.OK:
        return success(cmd[0])
    return error_code(f"{cmd[0]} failed!", rc)


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
                sys.exit(error_code_exc(subject, err))

            if result is True:
                sys.exit(success(subject))
            sys.exit(error_code(f"{subject} failed!"))

        return inner_function

    return inner_decorator

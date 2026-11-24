# pylint: disable=too-few-public-methods,line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import functools
import shutil
import subprocess as sp
import sys
import threading
import time
import traceback

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, NoReturn, Optional, ParamSpec

from .utils import Color, Output, RC, getenv_bool

__all__ = [
    "DEBUG",
    "DEBUG_HELP",
    "SHELL",
    "OUTPUT_LOCK",
    "print_error",
    "print_warning",
    "print_hint",
    "print_success",
    "print_test_cmd",
    "elapsed",
    "error_code",
    "error_code_exc",
    "failure",
    "success",
    "nothing_to_test",
    "require_commands",
    "run_shell_get_lines",
    "run_test_cmd",
    "run_tests",
    "run_tests_parallel",
    "boolean_test_decorator",
]

DEBUG = getenv_bool("TESTLIB_DEBUG")
DEBUG_HELP = "Set env TESTLIB_DEBUG=True for traceback."

# Override /bin/sh for bash on Debian/Ubuntu.
SHELL = "/bin/bash"

# Thread lock for parallel tests output.
OUTPUT_LOCK = threading.Lock()


def print_error(message: str, rc: int = RC.ERROR) -> None:
    if RC.is_early_exit(rc):
        color = Color.MAGENTA
    else:
        color = Color.RED

    print(color(message), file=sys.stderr)


def print_warning(message: str) -> None:
    print(Color.YELLOW(f"WARNING: {message}"), file=sys.stderr)


def print_hint(message: str) -> None:
    print(Color.BLUE(f"HINT: {message}"), file=sys.stderr)


def print_success(message: str) -> None:
    print(Color.GREEN(message), file=sys.stderr)


def print_test_cmd(cmd: List[str], targets: Optional[List[str]] = None, cwd: Optional[str] = None) -> None:
    message = Color.CYAN(f"Running: {Color.BOLD(' '.join(cmd))}")
    if cwd:
        message += f" @{cwd}"
    if targets:
        message += f" # {len(targets)} target(s)"
    if DEBUG:
        message += f" # at {time.strftime('%H:%M:%S')}"

    print(message, file=sys.stderr)


def elapsed(seconds: Optional[float], prefix: str = "") -> str:
    if seconds is None:
        return ""
    if seconds < 60:
        duration = f"{seconds:.2f}s"
    else:
        minutes, seconds_mod = divmod(round(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        duration = f"{hours}h {minutes}m {seconds_mod}s" if hours else f"{minutes}m {seconds_mod}s"

    if DEBUG:
        duration += f" at {time.strftime('%H:%M:%S')}"
    return f"{prefix}{duration}"


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
    if isinstance(err, KeyboardInterrupt):
        rc = RC.INTERRUPT
    elif isinstance(err, sp.TimeoutExpired):
        rc = RC.TIMEOUT
    elif isinstance(err, sp.CalledProcessError):
        rc = err.returncode
    else:
        rc = RC.ERROR

    if DEBUG:
        traceback.print_exception(err)
    elif not RC.is_early_exit(rc):
        print_hint(DEBUG_HELP)

    if isinstance(err, (KeyboardInterrupt, sp.TimeoutExpired, sp.CalledProcessError)):
        return failure(subject, rc, duration, sys_exit)

    return error_code(f"{subject} failed{elapsed(duration, ' after ')}: {err}", rc, sys_exit)


def failure(
    subject: str, rc: int = RC.ERROR, duration: Optional[float] = None, sys_exit: bool = False
) -> int | NoReturn:
    if not isinstance(rc, int):
        raise TypeError("testlib.failure called with non-integer rc")
    if rc == RC.OK:
        raise ValueError("testlib.failure called with RC.OK")

    if rc == RC.TIMEOUT:
        message = f"{subject} has timed out{elapsed(duration, ' after ')}!"
    elif RC.is_signal(rc):
        message = f"{subject} was interrupted{elapsed(duration, ' after ')}!"
    else:
        message = f"{subject} failed{elapsed(duration, ' after ')}!"

    return error_code(message, rc, sys_exit)


def success(subject: str, duration: Optional[float] = None, sys_exit: bool = False) -> int | NoReturn:
    print_success(f"{subject} passed{elapsed(duration, ' in ')}!")
    return RC.status(RC.OK, sys_exit)


def nothing_to_test(subject: str, sys_exit: bool = False) -> int | NoReturn:
    print_success(f"{subject}: nothing to test!")
    return RC.status(RC.OK, sys_exit)


def require_commands(*args: str) -> None | NoReturn:
    if missing := [name for name in args if shutil.which(name) is None]:
        print_hint("source venv/bin/activate")
        error_code(f"{', '.join(missing)} not found!", sys_exit=True)


def run_shell_get_lines(shell_cmd: str, *, null_delimited: bool = False, unique: bool = False, **kwargs) -> List[str]:
    # Passing encoding enables newline translation, which means losing \r with NULL-delimited strings.
    # Let callers control encoding and decode automatically below.
    try:
        result = sp.check_output(shell_cmd, executable=SHELL, shell=True, **kwargs)
    except (sp.SubprocessError, OSError, KeyboardInterrupt) as err:
        error_code_exc("testlib.run_shell_get_lines", err, sys_exit=True)

    if isinstance(result, bytes):
        result = result.decode(encoding="utf-8", errors="surrogateescape")

    if null_delimited:
        lines = result.split("\0")
        # Drop the trailing empty item left by the final NULL terminator or an empty result.
        if not lines[-1]:
            lines.pop(-1)
    else:
        lines = result.splitlines(keepends=False)

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


def run_tests(
    cmd: List[str], targets: Optional[List[str]] = None, *, sys_exit: bool = False, **kwargs
) -> int | NoReturn:
    if targets is not None and not targets:
        return nothing_to_test(cmd[0], sys_exit)

    require_commands(cmd[0])
    rc = run_test_cmd(cmd, targets or [], cmd[0], **kwargs)
    return RC.status(rc, sys_exit)


# If target items are dicts, 'args' (list) is appended to 'cmd', 'subject' (str) is generated if empty,
# and the rest (e.g. 'cwd') overrides kwargs passed to run_test_cmd.
def run_tests_parallel(
    cmd: List[str],
    targets: List[str | Dict[str, Any]],
    *,
    max_workers: Optional[int] = None,
    sys_exit: bool = False,
    **kwargs,
) -> int | NoReturn:
    if not targets:
        return nothing_to_test(cmd[0], sys_exit)

    require_commands(cmd[0])
    if "output" not in kwargs:
        kwargs["output"] = Output.BUFFERED_WITH_STATUS

    def run_test_job(target: str | Dict[str, Any]) -> int:
        if isinstance(target, dict):
            job_kwargs = kwargs.copy()
            job_kwargs.update(target)
            job_args = job_kwargs.pop("args", [])
            job_subject = job_kwargs.pop("subject", None) or f"{cmd[0]}: {' '.join(job_args) or '-'}"
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

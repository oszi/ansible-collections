# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import subprocess as sp
import sys

from typing import List

assert sys.version_info >= (3, 11)

# During a git hook execution stdout is not a terminal but
# colors are probably supported if stdin is a terminal.
STDIN_IS_TTY = os.isatty(sys.stdin.fileno())
STDOUT_IS_TTY = os.isatty(sys.stdout.fileno())

# External return codes.
RC_TIMED_OUT = 124
RC_NOT_FOUND = 127
RC_INTERRUPT = 130

# Override /bin/sh on Debian/Ubuntu for globbing.
SHELL = "/bin/bash"


# pylint: disable=too-few-public-methods
class Color:
    @staticmethod
    def code(code: int) -> str:
        return f"\033[{code}m" if STDIN_IS_TTY or STDOUT_IS_TTY else ""

    CLEAR = code(0)
    BOLD = code(1)
    HIGHLIGHT = code(7)
    RED = code(31)
    GREEN = code(32)
    YELLOW = code(33)
    BLUE = code(34)
    MAGENTA = code(35)
    CYAN = code(36)


def run_shell_get_lines(shell_cmd: str, unique: bool = False, **kwargs) -> List[str]:
    try:
        lines = sp.check_output(shell_cmd, executable=SHELL, shell=True, encoding="utf-8", **kwargs).splitlines()

    except KeyboardInterrupt:
        print(f"{Color.MAGENTA}testlib.run_shell_get_lines was interrupted!{Color.CLEAR}", file=sys.stderr)
        sys.exit(RC_INTERRUPT)

    except sp.TimeoutExpired:
        print(f"{Color.MAGENTA}testlib.run_shell_get_lines has timed out!{Color.CLEAR}", file=sys.stderr)
        sys.exit(RC_TIMED_OUT)

    except sp.CalledProcessError as e:
        print(f"{Color.YELLOW}{shell_cmd}{Color.CLEAR}", file=sys.stderr)
        print(f"{Color.RED}testlib.run_shell_get_lines failed!{Color.CLEAR}", file=sys.stderr)
        sys.exit(e.returncode)

    except FileNotFoundError:
        print(f"{Color.RED}testlib.SHELL={SHELL} not found!{Color.CLEAR}", file=sys.stderr)
        sys.exit(RC_NOT_FOUND)

    if unique:
        lines = list(set(lines))
    return lines


def run_tests(cmd: List[str], paths: List[str], timeout: float = None, **kwargs) -> int:
    if not isinstance(cmd, list):
        raise TypeError("cmd is not a list")
    if not isinstance(paths, list):
        raise TypeError("paths is not a list")

    print(
        f"{Color.CYAN}Running test: {Color.BOLD}{' '.join(cmd)}{Color.CLEAR}",
        f"# {len(paths)} path(s)" if paths else "",
        file=sys.stderr,
    )

    try:
        with sp.Popen(cmd + paths, encoding="utf-8", **kwargs) as proc:
            try:
                rc = proc.wait(timeout)
                if rc == 0:
                    print(f"{Color.GREEN}{cmd[0]} passed.{Color.CLEAR}", file=sys.stderr)
                else:
                    print(f"{Color.RED}{cmd[0]} failed!{Color.CLEAR}", file=sys.stderr)
                return rc

            except KeyboardInterrupt:
                print(f"{Color.MAGENTA}{cmd[0]} was interrupted!{Color.CLEAR}", file=sys.stderr)
                proc.terminate()
                return RC_INTERRUPT

            except sp.TimeoutExpired:
                print(f"{Color.MAGENTA}{cmd[0]} has timed out!{Color.CLEAR}", file=sys.stderr)
                proc.terminate()
                return RC_TIMED_OUT

    except FileNotFoundError:
        print(f"{Color.RED}{cmd[0]} not found!{Color.CLEAR}", file=sys.stderr)
        return RC_NOT_FOUND

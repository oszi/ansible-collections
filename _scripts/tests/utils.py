# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,missing-module-docstring
import os
import subprocess as sp
import sys

from typing import List

assert sys.version_info >= (3, 11)

# During a git hook execution stdout is not a terminal but
# colors are probably supported if stdin is a terminal.
STDIN_IS_ATTY = os.isatty(sys.stdin.fileno())


# pylint: disable=too-few-public-methods
class Color:
    @staticmethod
    def code(code: int) -> str:
        return f"\033[{code}m" if STDIN_IS_ATTY else ""

    CLEAR = code(0)
    BOLD = code(1)
    HIGHLIGHT = code(7)
    RED = code(31)
    GREEN = code(32)
    YELLOW = code(33)
    BLUE = code(34)
    MAGENTA = code(35)
    CYAN = code(36)


def run_shell(shell_cmd: str, **kwargs) -> List[str]:
    return sp.check_output(shell_cmd, encoding="utf-8", shell=True, **kwargs).splitlines()


def run_tests(cmd: List[str], paths: List[str], **kwargs) -> int:
    if not isinstance(cmd, list):
        raise TypeError("cmd is not a list")
    if not isinstance(paths, list):
        raise TypeError("paths is not a list")

    try:
        with sp.Popen(cmd + paths, encoding="utf-8", **kwargs) as proc:
            rc = proc.wait()

            if rc != 0:
                print(f"{Color.RED}{cmd[0]} failed!{Color.CLEAR}", file=sys.stderr)
            elif paths:
                print(f"{Color.GREEN}{cmd[0]} passed on{Color.CLEAR}: {len(paths)} files", file=sys.stderr)

            return rc

    except FileNotFoundError:
        print(f"{Color.RED}{cmd[0]} not found!{Color.CLEAR}", file=sys.stderr)
        return 1

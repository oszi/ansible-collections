#!/bin/bash
# Script to run all or the given tests.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
shopt -s nullglob
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

if [[ -t 0 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
fi

tests_dir="_scripts/tests"
if ! [[ -d "$tests_dir" ]]; then
    tests_dir="collections/${tests_dir}"
    if ! [[ -d "$tests_dir" ]]; then
        printf "${COLOR_RED}%q not found!${COLOR_CLEAR}\n" "$tests_dir" >&2
        exit 127
    fi
fi

# Run all tests by default.
if [[ $# -eq 0 ]]; then
    tests=("$tests_dir"/*.py)
elif [[ "$1" =~ ^-*(h|help)$ ]]; then
    echo "Usage: ${0} [-h|--help] | [TESTS ...]" >&2
    basename -a -s .py "$tests_dir"/*.py 2>/dev/null | grep -v testlib >&2
    exit 2
else
    tests=("${@/#/"$tests_dir"/}")
    tests=("${tests[@]/%/.py}")
fi

rc=0
for cmd in "${tests[@]}"; do
    if [[ -f "$cmd" && -x "$cmd" ]]; then
        "$cmd" || (( rc=1 ))
    elif [[ $# -gt 0 ]]; then
        printf "${COLOR_RED}%q not found!${COLOR_CLEAR}\n" "$cmd" >&2
        (( rc=1 ))
    fi
done

if [[ $rc -ne 0 ]]; then
    printf "${COLOR_RED}%q failed!${COLOR_CLEAR}\n" "$0" >&2
fi

exit $rc

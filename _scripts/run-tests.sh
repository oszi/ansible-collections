#!/bin/bash
# Script to run all or the given tests.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
shopt -s nullglob
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

# During a git hook execution stdout is not a terminal but
# colors are probably supported if stdin is a terminal.
if [[ -t 1 ]]; then
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
        echo -e "${COLOR_RED}${tests_dir} not found!${COLOR_CLEAR}" >&2
        exit 1
    fi
fi

# Run all tests by default.
if [[ $# -eq 0 ]]; then
    tests=("$tests_dir"/*)
elif [[ "${1-}" =~ ^-*(h|help)$ ]]; then
    echo "Usage: $0 [ansible-lint] [python] [shellcheck] ..." >&2
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
        echo -e "${COLOR_RED}${cmd} not found!${COLOR_CLEAR}" >&2
        (( rc=1 ))
    fi
done
exit $rc

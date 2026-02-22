#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

# During a git hook execution stdout is not a terminal but
# colors are probably supported if stdin is a terminal.
if [[ -t 1 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_YELLOW="\033[33m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_YELLOW=""
fi

run_linters=0
# Skip linters by default and if stdin is not a terminal.
if [[ $# -eq 0 ]]; then
    if [[ -t 1 ]]; then
        exec < /dev/tty
        echo -en "${COLOR_YELLOW}Run ansible-lint and linters for scripts?${COLOR_CLEAR} [y/N]" >&2
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            run_linters=1
        fi
    fi
elif [[ "${1-}" =~ ^(-f|--force|-y|--yes)$ ]]; then
    run_linters=1
else
    echo "Usage: ${0} [-f|--force|-y|--yes]" >&2
    exit 2
fi

run_tests() {
    local cmd="_scripts/tests/${1}"

    if [[ -x "$cmd" ]]; then
        "$cmd"
        return $?
    elif [[ -x "collections/${cmd}" ]]; then
        "collections/${cmd}"
        return $?
    else
        echo -e "${COLOR_RED}${cmd} not found!${COLOR_CLEAR}" >&2
        return 1
    fi
}

rc=0
if [[ "$run_linters" -ne 0 ]]; then
    run_tests ansible-lint.py || (( rc=1 ))
    run_tests galaxy-tags.py  || (( rc=1 ))
    run_tests shellcheck.py   || (( rc=1 ))
    run_tests python.py       || (( rc=1 ))
fi

run_tests ansible-vault.py    || (( rc=1 ))
exit $rc

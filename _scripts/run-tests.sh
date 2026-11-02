#!/bin/bash
# Script to run all or the given tests.
# You may symlink this file into a parent repository - e.g. inventory.
# shellcheck disable=SC1091 # not following input sources
set -euo pipefail
shopt -s nullglob
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

if [ -z "${VIRTUAL_ENV-}" ]; then
    if [ -d venv ]; then
        . venv/bin/activate
    elif [ -d collections/venv ]; then
        . collections/venv/bin/activate
    fi
fi

if [[ -t 2 ]]; then  # stderr
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
fi

exit_with_error() {
    printf "${COLOR_RED}run-tests: %s${COLOR_CLEAR}\n" "${1//[[:cntrl:]]/}" >&2
    exit 1
}

exit_with_not_found() {
    printf "${COLOR_RED}%s not found!${COLOR_CLEAR}\n" "${1//[[:cntrl:]]/}" >&2
    exit 127
}

tests_dir="_scripts/tests"
if ! [[ -d "$tests_dir" ]]; then
    tests_dir="collections/${tests_dir}"
    if ! [[ -d "$tests_dir" ]]; then
        exit_with_not_found "$tests_dir"
    fi
fi

all_tests=()
for test in "$tests_dir"/*.py; do
    [[ "$test" == */testlib.py ]] || all_tests+=("$(basename -s .py "$test")")
done

is_test() {
    local test
    for test in "${all_tests[@]}"; do
        [[ "$1" == "$test" ]] && return 0
    done
    return 1
}

is_opt_in() {
    local test="$1"
    grep -q '^# run-tests: opt-in$' -- "${tests_dir}/${test}.py"
}

# Tests to run, with the slice of $args passed to each.
names=() starts=() lengths=() args=()

# Run all tests by default, except opt-in tests (e.g. molecule).
if [[ $# -eq 0 ]]; then
    for test in "${all_tests[@]}"; do
        is_opt_in "$test" && continue
        names+=("$test") starts+=(0) lengths+=(0)
    done
elif [[ "$1" =~ ^-*(h|help)$ ]]; then
    echo "Usage: ${0} [-h|--help] [TEST [ '[' TEST_ARGS ... ']' ]] ..." >&2
    for test in "${all_tests[@]}"; do
        is_opt_in "$test" && suffix=" (opt-in)" || suffix=""
        echo "${test}${suffix}" >&2
    done
    exit 2
else
    # Words outside brackets are test names; test arguments may equal test names or contain "--".
    # A literal "]" cannot be passed; run the test script directly instead.
    in_args=0 can_open=0
    for arg in "$@"; do
        if (( in_args )); then
            if [[ "$arg" == "]" ]]; then
                in_args=0
            else
                args+=("$arg")
                lengths[-1]=$(( lengths[-1] + 1 ))
            fi
        elif [[ "$arg" == "[" ]]; then
            (( can_open )) || exit_with_error "'[' must follow a test name!"
            in_args=1 can_open=0
        elif [[ "$arg" == "]" ]]; then
            exit_with_error "']' unmatched!"
        elif is_test "$arg"; then
            names+=("$arg") starts+=("${#args[@]}") lengths+=(0)
            can_open=1
        else
            exit_with_not_found "${tests_dir}/${arg}.py"
        fi
    done
    (( ! in_args )) || exit_with_error "'[' unclosed!"
fi

rc=0
for i in "${!names[@]}"; do
    cmd="${tests_dir}/${names[i]}.py"
    if [[ -x "$cmd" ]]; then
        "$cmd" "${args[@]:starts[i]:lengths[i]}" || rc=1
    elif [[ $# -gt 0 ]]; then
        printf "${COLOR_RED}%q is not executable!${COLOR_CLEAR}\n" "$cmd" >&2
        rc=1
    fi
done

if [[ $rc -ne 0 ]]; then
    printf "${COLOR_RED}%s${COLOR_CLEAR}\n" "run-tests failed!" >&2
fi

exit $rc

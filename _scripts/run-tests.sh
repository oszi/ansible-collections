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

print_error() {
    printf "${COLOR_RED}run-tests: %s${COLOR_CLEAR}\n" "${1//[[:cntrl:]]/}" >&2
}

exit_with_error() {
    print_error "$1"
    exit 1
}

exit_with_not_found() {
    print_error "${1} not found!"
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

# Tests that run only when requested by name or with --all.
opt_in=(molecule)

# Tests that accept --all themselves to test everything, not only changes since the previous release.
all_supported=(ansible-lint molecule)

in_list() {
    local item needle="$1"
    shift

    for item in "$@"; do
        [[ "$needle" == "$item" ]] && return 0
    done
    return 1
}

# Tests to run; each test's arguments are its slice of $args.
names=() starts=() lengths=() args=()

add_test() {  # NAME [ARG ...]
    names+=("$1")
    starts+=("${#args[@]}")
    lengths+=($(( $# - 1 )))
    args+=("${@:2}")
}

add_arg() {  # To the last added test.
    args+=("$1")
    lengths[-1]=$(( lengths[-1] + 1 ))
}

exit_with_usage() {
    local test all_suffix opt_in_suffix

    echo "Usage: ${0} [-h|--help] [--all | TEST [ '[' TEST_ARGS ... ']' ] ...]" >&2
    for test in "${all_tests[@]}"; do
        in_list "$test" "${all_supported[@]}" && all_suffix=" (--all)" || all_suffix=""
        in_list "$test" "${opt_in[@]}" && opt_in_suffix=" (opt-in)" || opt_in_suffix=""
        printf "%s%s%s\n" "$test" "$all_suffix" "$opt_in_suffix"
    done
    exit 2
}

# Words outside brackets are test names; test arguments may equal test names or contain "--".
# A literal "]" cannot be passed; run the test script directly instead.
parse_test_args() {
    local arg in_args=0 after_name=0

    for arg in "$@"; do
        if (( in_args )); then
            if [[ "$arg" == "]" ]]; then
                in_args=0
            else
                add_arg "$arg"
            fi
        elif [[ "$arg" == "[" ]]; then
            (( after_name )) || exit_with_error "'[' must follow a test name!"
            in_args=1 after_name=0
        elif [[ "$arg" == "]" ]]; then
            exit_with_error "']' unmatched!"
        elif in_list "$arg" "${all_tests[@]}"; then
            add_test "$arg"
            after_name=1
        else
            exit_with_not_found "${tests_dir}/${arg}.py"
        fi
    done
    (( ! in_args )) || exit_with_error "'[' unclosed!"
}

if [[ $# -eq 0 ]]; then
    for test in "${all_tests[@]}"; do
        in_list "$test" "${opt_in[@]}" || add_test "$test"
    done
elif [[ "$1" == "--all" ]]; then
    (( $# == 1 )) || exit_with_error "--all takes no other arguments!"
    for test in "${all_tests[@]}"; do
        if in_list "$test" "${all_supported[@]}"; then
            add_test "$test" --all
        else
            add_test "$test"
        fi
    done
elif [[ "$1" =~ ^(-h|--help)$ ]]; then
    exit_with_usage
else
    parse_test_args "$@"
fi

rc=0
failed=()
for i in "${!names[@]}"; do
    cmd="${tests_dir}/${names[i]}.py"
    "$cmd" "${args[@]:starts[i]:lengths[i]}" || {
        failed+=("${names[i]}")
        rc=1
    }
done

if [[ $rc -ne 0 && "${#names[@]}" -gt 1 ]]; then
    print_error "tests failed: ${failed[*]}"
fi

if [[ -t 1 ]] && (( SECONDS >= 3 )); then  # stdout; skip for quick runs
    printf "\007"
fi

exit $rc

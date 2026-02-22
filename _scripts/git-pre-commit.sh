#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

run_tests="_scripts/run-tests.sh"
if ! [[ -f "$run_tests" ]]; then
    run_tests="collections/${run_tests}"
    if ! [[ -f "$run_tests" ]]; then
        echo "${run_tests} not found!" >&2
        exit 1
    fi
fi

if [[ $# -ne 0 ]]; then
    echo "Usage: ${0}" >&2
    echo "See also: ${run_tests}" >&2
    exit 2
fi

"$run_tests" ansible-vault

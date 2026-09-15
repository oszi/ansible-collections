#!/bin/bash
# Script to verify the signatures of git branches and tags; use user keyring per environment.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

if [[ -t 0 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_GREEN="\033[32m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_GREEN=""
fi

git_verify() {
    local cmd="verify-${1}"

    if xargs -rd'\n' git "$cmd" -v --; then
        echo -e "${COLOR_GREEN}${cmd} [OK]${COLOR_CLEAR}" >&2
        return 0
    else
        echo -e "${COLOR_RED}${cmd} [FAIL]${COLOR_CLEAR}" >&2
        return 1
    fi
}

if (( $# )); then
    rc=0
    for ref do
        if [[ "$ref" == refs/tags/* ]] || git show-ref --quiet --verify -- "refs/tags/${ref}"; then
            git_verify tag <<<"$ref" || (( rc=1 ))
        else
            git_verify commit <<<"$ref" || (( rc=1 ))
        fi
    done
    exit $rc
else
    git branch -a --format='%(refname)' | grep -Ev '^\(' | git_verify commit || exit 1
    git tag -l --sort=version:refname | git_verify tag || exit 1
fi

#!/bin/bash
# Script to verify the signatures of git branches and tags; use user keyring per environment.
# XXX: For revoked/compromised keys, implement a trust-anchor tag and use merge-base --is-ancestor.
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

git_verify_cmd() {
    local cmd="verify-${1}"

    if xargs -rd'\n' git "$cmd" -v --; then
        echo -e "${COLOR_GREEN}${cmd} [OK]${COLOR_CLEAR}" >&2
        return 0
    else
        echo -e "${COLOR_RED}${cmd} [FAIL]${COLOR_CLEAR} (search 'error:')" >&2
        return 1
    fi
}

git_verify_ref() {
    local ref="$1"

    if [[ "$(git cat-file -t -- "$ref" 2>/dev/null)" = "tag" ]]; then
        git_verify_cmd tag <<<"$ref"
    else
        git_verify_cmd commit <<<"$ref"
    fi
}

if (( $# )); then
    rc=0
    for ref do
        git_verify_ref "$ref" || (( rc=1 ))
    done
    exit $rc
else
    git branch -a --format='%(refname)' \
        | grep -Ev '^\(' \
        | git_verify_cmd commit || exit 1

    git for-each-ref --format='%(objecttype) %(refname)' --sort=version:refname refs/tags/ \
        | awk '$1 == "tag" {print $2}' \
        | git_verify_cmd tag || exit 1
fi

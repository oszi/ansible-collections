#!/bin/bash
# Script to verify and reset the git repository.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

fetch_opts=(--atomic)

if [[ "${1-}" =~ ^(-f|--force)$ ]]; then
    fetch_opts+=(--force --tags --prune --prune-tags)
    shift
elif [[ "${1-}" =~ ^-.*$ ]]; then
    echo "Usage: ${0} [-f|--force] [[REMOTE(origin)] BRANCH(master)]" >&2
    exit 2
fi

if [[ $# -gt 1 ]]; then
    REMOTE="$1"
    BRANCH="$2"
else
    REMOTE="origin"
    BRANCH="${1:-master}"
fi

UPSTREAM="${REMOTE}/${BRANCH}"
fetch_opts+=("$REMOTE")

COLOR_CLEAR="\033[0m"
COLOR_RED="\033[31m"

answer_yes_or_exit() {
    echo -en "${COLOR_RED}${1}${COLOR_CLEAR} [y/N]" >&2
    read -r answer
    if ! [[ "$answer" =~ ^[Yy] ]]; then
        exit 1
    fi
}

if ! git fetch "${fetch_opts[@]}"; then
    answer_yes_or_exit "git: remote fetch failed! Continue anyway?"
fi

if ! git verify-commit "$UPSTREAM"; then
    answer_yes_or_exit "git: signature verification failed! Continue anyway?"
fi

if [[ "$(git status -s | tee /dev/stderr)" != "" ]]; then
    answer_yes_or_exit "git: working tree changes! Discard everything?"
fi

if [[ "$(git log --ignore-missing "${UPSTREAM}..${BRANCH}" -- | tee /dev/stderr)" != "" ]]; then
    answer_yes_or_exit "git: local commits! Discard everything?"
fi

git switch -fC "$BRANCH" "$UPSTREAM"
git clean -xfd

git submodule update --recursive --force --init --checkout
git submodule foreach --recursive git clean -xfd

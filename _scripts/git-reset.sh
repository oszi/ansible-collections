#!/bin/bash
# Script to verify and reset the git repository.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

fetch_opts=(--atomic --porcelain)
force=0

if [[ "${1-}" =~ ^(-f|--force)$ ]]; then
    fetch_opts+=(--force --tags --prune --prune-tags)
    force=1
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
COLOR_YELLOW="\033[33m"

answer_yes_or_exit() {
    echo -en "${COLOR_RED}${1}${COLOR_CLEAR} [y/N]" >&2
    read -r answer
    if ! [[ "$answer" =~ ^[Yy] ]]; then
        exit 1
    fi
}

print_section() {
    echo -e "${COLOR_YELLOW}${1}${COLOR_CLEAR}" >&2
}

fetch_logs="$(git fetch "${fetch_opts[@]}" | tee /dev/stderr)" \
    || answer_yes_or_exit "git: remote fetch failed! Continue anyway?"

(grep -E '^[^-].+refs/tags/' <<< "$fetch_logs" | grep -Eo 'refs/tags/\S+' ||:) \
    | xargs -r -d'\n' git verify-tag -v -- \
    || answer_yes_or_exit "git: verify-tag failed! Continue anyway?"

print_section "Verify ${UPSTREAM}^..$(git log --oneline "${UPSTREAM}^..${UPSTREAM}" -- 2>/dev/null)"

git verify-commit "$UPSTREAM" \
    || answer_yes_or_exit "git: verify-commit failed! Continue anyway?"

print_section "Check working tree and local commits..."

[[ "$(git status -s | tee /dev/stderr)" = "" ]] \
    || answer_yes_or_exit "git: working tree changes! Discard everything?"

[[ "$(git log --ignore-missing "${UPSTREAM}..${BRANCH}" -- | tee /dev/stderr)" = "" ]] \
    || answer_yes_or_exit "git: local commits! Discard everything?"

print_section "Reset branch and clean up..."

git switch -fC "$BRANCH" "$UPSTREAM"
git submodule update --recursive --force --init --checkout

if [[ "$force" -ne 0 ]]; then
    git clean -xfd
    git submodule foreach --recursive git clean -xfd
fi

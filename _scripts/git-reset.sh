#!/bin/bash
# Script to verify and reset the git repository.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

fetch_opts=(--atomic)
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

REFERENCE="refs/remotes/${REMOTE}/${BRANCH}"
fetch_opts+=("$REMOTE")

if [[ -t 0 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_YELLOW="\033[33m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_YELLOW=""
fi

answer_yes_or_exit() {
    echo -en "${COLOR_RED}${1}${COLOR_CLEAR} [y/N]" >&2
    read -r answer
    if ! [[ "$answer" =~ ^[Yy] ]]; then
        exit 1
    fi
}

exit_with_error() {
    echo -e "${COLOR_RED}${1}${COLOR_CLEAR}" >&2
    exit 1
}

print_section() {
    echo -e "${COLOR_YELLOW}${1}${COLOR_CLEAR}" >&2
}

print_section "git: Fetch ${REMOTE} [${fetch_opts[*]:0:${#fetch_opts[@]}-1}]"

git fetch "${fetch_opts[@]}" \
    || answer_yes_or_exit "git: Remote fetch failed! Continue anyway?"

git show-ref --quiet --verify -- "${REFERENCE}" \
    || exit_with_error "git: Branch not found: ${REFERENCE}"

print_section "git: Verify commit $(git log --oneline "${REFERENCE}^..${REFERENCE}" -- 2>/dev/null)"

git verify-commit "$REFERENCE" \
    || answer_yes_or_exit "git: Verify-commit failed! Continue anyway?"

print_section "git: Check working tree and local commits..."

[[ "$(git status -s | tee /dev/stderr)" = "" ]] \
    || answer_yes_or_exit "git: Working tree changes! Discard everything?"

[[ "$(git log --ignore-missing "${REFERENCE}..${BRANCH}" -- | tee /dev/stderr)" = "" ]] \
    || answer_yes_or_exit "git: Local commits! Discard everything?"

print_section "git: Reset branch and clean up..."

git switch -fC "$BRANCH" "$REFERENCE"
git submodule update --recursive --force --init --checkout

if [[ "$force" -ne 0 ]]; then
    git clean -xfd
    git submodule foreach --recursive git clean -xfd
fi

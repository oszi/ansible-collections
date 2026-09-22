#!/bin/bash
# Script to verify and reset the git repository.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

fetch_opts=(--atomic)

if [[ "${1-}" =~ ^(-f|--force)$ ]]; then
    fetch_opts+=(--force --tags --prune --prune-tags)
    shift
fi

if [[ "${1-}" =~ ^(-h|--help)$ ]]; then
    echo "Usage: ${0} [-f|--force] [[REMOTE(origin)] BRANCH(master)]" >&2
    exit 2
fi

if [[ $# -gt 1 ]]; then
    REMOTE="$1"
    BRANCH="$2"
else
    REMOTE="origin"
    BRANCH="${1-master}"
fi

REFERENCE="refs/remotes/${REMOTE}/${BRANCH}"
fetch_opts+=(-- "$REMOTE")

if [[ -t 2 ]]; then  # stderr
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_YELLOW="\033[33m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_YELLOW=""
fi

answer_yes_or_exit() {
    printf "${COLOR_RED}%s${COLOR_CLEAR} [y/N]" "${1//[[:cntrl:]]/}" >&2
    read -r answer
    if ! [[ "$answer" =~ ^[Yy] ]]; then
        exit 1
    fi
}

exit_with_error() {
    printf "${COLOR_RED}%s${COLOR_CLEAR}\n" "${1//[[:cntrl:]]/}" >&2
    exit 1
}

print_section() {
    printf "${COLOR_YELLOW}%s${COLOR_CLEAR}\n" "${1//[[:cntrl:]]/}" >&2
}

tee_sanitized() {
    tr -d '\000-\010\013-\037\177' | tee /dev/stderr
}

print_section "git: Fetch ${fetch_opts[*]}"

git fetch "${fetch_opts[@]}" \
    || answer_yes_or_exit "git: Remote fetch failed! Continue anyway?"

git show-ref --quiet --verify -- "${REFERENCE}" \
    || exit_with_error "git: Branch not found: ${REFERENCE}"

print_section "git: Verify commit $(git log -1 --oneline "$REFERENCE" --)"

git verify-commit -- "$REFERENCE" \
    || answer_yes_or_exit "git: Verify-commit failed! Continue anyway?"

print_section "git: Check working tree and local commits..."

[[ "$(git status -s 2>&1 | tee_sanitized)" = "" ]] \
    || answer_yes_or_exit "git: Working tree changes! Discard everything?"

[[ "$(git log --ignore-missing --oneline "${REFERENCE}..${BRANCH}" -- 2>&1 | tee_sanitized)" = "" ]] \
    || answer_yes_or_exit "git: Local commits! Discard everything?"

print_section "git: Reset branch and submodules..."

git switch -fC "$BRANCH" "$REFERENCE"
git submodule update --recursive --force --init --checkout

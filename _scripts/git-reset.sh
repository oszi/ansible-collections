#!/bin/bash
# Script to verify and reset the git repository.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

DEFAULT_BRANCH="master"
UPSTREAM="origin/${DEFAULT_BRANCH}"

COLOR_CLEAR="\033[0m"
COLOR_RED="\033[31m"

answer_yes_or_exit() {
  echo -en "${COLOR_RED}${1}${COLOR_CLEAR} [y/N]" >&2
  read answer
  if ! echo "${answer}" | grep -iq '^Y'; then
    exit 1
  fi
}

if ! git fetch origin; then
  answer_yes_or_exit "git: origin fetch failed! Continue anyway?"
fi

if ! git verify-commit "${UPSTREAM}"; then
  answer_yes_or_exit "git: signature verification failed! Continue anyway?"
fi

if [[ "$(git status -s | tee /dev/stderr)" != "" ]]; then
  answer_yes_or_exit "git: working tree changes! Discard everything?"
fi

if [[ "$(git log "${UPSTREAM}..${DEFAULT_BRANCH}" | tee /dev/stderr)" != "" ]]; then
  answer_yes_or_exit "git: local commits! Discard everything?"
fi

git switch -fC "${DEFAULT_BRANCH}" "${UPSTREAM}"
git clean -fdxxx
git submodule update --force --init --checkout --recursive

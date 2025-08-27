#!/bin/bash
# Script to verify the signatures of all git branches and tags.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

GPG_KEY_ID="AFDE0AB3943D1FB3"
GPG_IMPORT_URL="https://oszi.dev/oszi.dev.asc"

if [[ -t 0 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_GREEN="\033[32m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_GREEN=""
fi

if [[ -t 1 ]] && ! gpg -k "$GPG_KEY_ID"; then
    echo -en "Import GPG key: ${GPG_KEY_ID} from ${GPG_IMPORT_URL}? [y/N]" >&2
    read -r answer
    if [[ "$answer" =~ ^[Yy] ]]; then
        curl -sL "$GPG_IMPORT_URL" | gpg --import -
    fi
fi

xargs_git() {
    if xargs -r -d'\n' git "$@" -v --; then
        echo -e "${COLOR_GREEN}git $* succeeded${COLOR_CLEAR}" >&2
        return 0
    else
        echo -e "${COLOR_RED}git $* failed${COLOR_CLEAR}" >&2
        return 1
    fi
}

git branch -a --format='%(refname)' | grep -Ev '^\(' | xargs_git verify-commit
git tag -l | xargs_git verify-tag

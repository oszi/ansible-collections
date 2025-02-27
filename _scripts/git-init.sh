#!/bin/bash
# Script to initialize the git repository.
# You may call this script in a parent repository, like so:

##!/bin/bash
#set -euo pipefail
#cd -- "$(git rev-parse --show-toplevel)"
#git submodule update --init --checkout --recursive
#collections/_scripts/git-init.sh

set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"
git submodule update --init --checkout --recursive

hooks_path="$(git rev-parse --git-dir)/hooks"
hooks=(
    pre-commit
    post-commit
    pre-merge-commit
    pre-rebase
    post-checkout
    pre-receive
    post-receive
    pre-push
)

setup_hook() {
    local hook="$1"
    local script="_scripts/git-${hook}.sh"

    if [[ -x "$script" ]]; then
        ln -s -r -f -v "$script" "${hooks_path}/${hook}"
    fi
}

for hook in "${hooks[@]}"; do
    setup_hook "$hook"
done

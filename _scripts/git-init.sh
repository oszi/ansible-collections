#!/bin/bash
# Script to initialize the git repository.
# You may copy this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

git log --oneline HEAD^..HEAD --
git verify-commit HEAD

git submodule update --init --checkout --recursive

if [ -e _scripts/git-pre-commit.sh ]; then
    ln -sfv ../../_scripts/git-pre-commit.sh .git/hooks/pre-commit
fi

#!/bin/bash
# Script to initialize the git repository.
# You may COPY this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

git submodule update --init --checkout --recursive

if [[ -r _scripts/git-pre-commit.sh ]]; then
    ln -sfv ../../_scripts/git-pre-commit.sh .git/hooks/pre-commit
fi

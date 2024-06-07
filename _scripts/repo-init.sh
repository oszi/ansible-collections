#!/bin/bash
set -euo pipefail
cd "$(dirname "$(realpath "$0")")/.."

ln -sfv ../../_scripts/pre-commit.sh .git/hooks/pre-commit
git submodule update --force --init --checkout --recursive

#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec < /dev/tty

if [[ ! -e .ansible-lint && -d ansible ]]; then
  cd ansible  # alternative location in a submodule?
fi

echo -n "Run ansible-lint? [y/N]" >&2
read answer
if echo "${answer}" | grep -iq '^Y'; then
  ansible-lint
fi

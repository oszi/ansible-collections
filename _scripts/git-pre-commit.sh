#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"
exec < /dev/tty

if [[ ! -e ansible.cfg && -d ansible ]]; then
  cd ansible  # (e.g. in a submodule)
fi

GREP_ANSIBLE_VAULT='grep --files-without-match ^$ANSIBLE_VAULT'

files="$(find -type f \( -iname '*-key.pem' -or -iname '*.key' -or -iname '*.csr' -or -iname '*.p12' \) -print0 2>/dev/null \
  | xargs -0 -r -n4 ${GREP_ANSIBLE_VAULT})" ||:

if [ "$files" != "" ]; then
  echo "# Clear-text private keys found!" >&2
  echo "$files" >&2
  exit 1
fi

files="$(find -type f -wholename '*/*_vars/*' \( -iname '*vault*.yml' -or -iname '*vault*.yaml' \) -print0 2>/dev/null \
  | xargs -0 -r -n4 ${GREP_ANSIBLE_VAULT})" ||:

if [ "$files" != "" ]; then
  echo "# Clear-text vault files found!" >&2
  echo "$files" >&2
  exit 1
fi

echo -n "Run ansible-lint? [y/N]" >&2
read answer
if echo "$answer" | grep -iq '^Y'; then
  ansible-lint
fi

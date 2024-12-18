#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"
exec < /dev/tty

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

COLOR_CLEAR="\033[0m"
COLOR_RED="\033[31m"
COLOR_YELLOW="\033[33m"

VAULT_FILES_REGEX='^.*/\(group\|host\)_vars/.*vault[^/]*\.\(ya?ml\|json\)$'
KEY_FILES_REGEX='^.*\(\(private\|privkey\|-key\)\.pem\|\.key\|\.csr\|\.p12\)$'

# shellcheck disable=SC2016 # quoting '^$ANSIBLE_VAULT'
files="$(find . -type f \( -regex "$VAULT_FILES_REGEX" -or -regex "$KEY_FILES_REGEX" \) -print0 2>/dev/null \
    | xargs -0 -r grep --files-without-match -- '^$ANSIBLE_VAULT')" ||:

if [ "$files" != "" ]; then
    echo -e "${COLOR_RED}Clear-text private keys or vault files!${COLOR_CLEAR}" >&2
    echo "$files"
    exit 1
fi

echo -en "${COLOR_YELLOW}Run ansible-lint?${COLOR_CLEAR} [y/N]" >&2
read -r answer
if [[ "$answer" =~ ^[Yy] ]]; then
    ansible-lint
fi

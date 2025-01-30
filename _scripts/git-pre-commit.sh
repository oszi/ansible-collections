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
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"

VAULT_FILES_REGEX='.*/\(group\|host\)_vars/.*vault[^/]*\.\(ya?ml\|json\)$'
KEY_FILES_REGEX='.*\(\(private\|privkey\|-key\)\.pem\|\.key\|\.csr\|\.p12\)$'

# shellcheck disable=SC2016 # quoting '^$ANSIBLE_VAULT'
vault_files="$(find . -type f \( -iregex "$VAULT_FILES_REGEX" -or -iregex "$KEY_FILES_REGEX" \) -print0 \
    | xargs -0 -r grep --files-without-match -- '^$ANSIBLE_VAULT')" ||:

if [[ "$vault_files" != "" ]]; then
    echo -e "${COLOR_RED}Clear-text private keys or vault files!${COLOR_CLEAR}" >&2
    echo "$vault_files"
    exit 1
fi

SHELL_FILES_REGEX='.*\(\.\(sh\|bash\|ksh\|zsh\)\|[/.]\w*\(shrc\|profile\)\)$'
SHELL_PATHS_REGEX='.*/\(_*scripts\|s?bin\)/.+$'
AWK_SHEBANG_MATCH='FNR>1 {nextfile} /^#![^ ]+[/ ](sh|bash|ksh|zsh)$/ {print FILENAME; nextfile}'

shellcheck-targets() {
    find . -type f -iregex "$SHELL_FILES_REGEX"

    find . -type f -iregex "$SHELL_PATHS_REGEX" \
        -not -iregex "$SHELL_FILES_REGEX" -not -iregex '.*\.\(j2\|jinja\)$' -print0 \
        | xargs -0 -r awk -- "$AWK_SHEBANG_MATCH"
}

shellcheck-lint() {
    if ! command -v shellcheck >/dev/null 2>&1; then
        echo -e "${COLOR_RED}shellcheck is not installed! skipping...${COLOR_CLEAR}" >&2
        return 0
    fi

    local IFS=$'\n'
    local targets

    read -r -a targets -d '' < <(shellcheck-targets | sort -u) ||:
    if [[ -n "${targets-}" ]]; then
        shellcheck -- "${targets[@]}" || exit 1
        echo -e "${COLOR_GREEN}shellcheck passed${COLOR_CLEAR}: on ${#targets[@]} files." >&2
    fi
}

echo -en "${COLOR_YELLOW}Run ansible-lint and shellcheck?${COLOR_CLEAR} [y/N]" >&2
read -r answer
if [[ "$answer" =~ ^[Yy] ]]; then
    ansible-lint && shellcheck-lint
fi

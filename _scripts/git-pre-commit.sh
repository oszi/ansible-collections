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

if ! [[ "${1-}" =~ ^-*(y|yes|f|force)$ ]]; then
    echo -en "${COLOR_YELLOW}Run ansible-lint and shellcheck?${COLOR_CLEAR} [y/N]" >&2
    read -r answer
    if ! [[ "$answer" =~ ^[Yy] ]]; then
        exit 0
    fi
fi

GIT_LS_FILES='git ls-files -c -o --exclude-standard --deduplicate'

vault_files=$(
    ${GIT_LS_FILES} -z -- '**_vars/**vault.'{yaml,yml,json} '*.'{key,csr,p12} '**/'{private,privkey,\*-key}.pem \
        | xargs -0 -r grep --files-without-match -- $'^$ANSIBLE_VAULT'
) ||:

if [[ "$vault_files" != "" ]]; then
    echo -e "${COLOR_RED}Clear-text private keys or vault files!${COLOR_CLEAR}" >&2
    echo "$vault_files"
    exit 1
fi

shellcheck-targets() {
    local IFS=' '

    ${GIT_LS_FILES} -- '*.'{sh,bash,ksh,zsh} '**/*shrc' '**/.*profile'
    ${GIT_LS_FILES} -z -- '**scripts/*' '**/bin/*' '**/sbin/*' ':!:*.'{j2,jinja} \
        | xargs -0 -r awk -- 'FNR>1 {nextfile} /^#![^ ]+[/ ](sh|bash|ksh|zsh)$/ {print FILENAME; nextfile}'
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

ansible-lint && shellcheck-lint

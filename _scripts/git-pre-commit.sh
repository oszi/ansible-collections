#!/bin/bash
# Script to run before git commits.
# You may symlink this file into a parent repository - e.g. inventory.
# XXX: Rewrite this script in python with configurable CLI options.
set -euo pipefail
cd -- "$(git rev-parse --show-toplevel)"

if [[ ! -e ansible.cfg && -d ansible ]]; then
    cd ansible  # (e.g. in a submodule)
fi

# During a git hook execution stdout is not a terminal but
# colors are probably supported if stdin is a terminal.
if [[ -t 1 ]]; then
    COLOR_CLEAR="\033[0m"
    COLOR_RED="\033[31m"
    COLOR_GREEN="\033[32m"
    COLOR_YELLOW="\033[33m"
else
    COLOR_CLEAR=""
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_YELLOW=""
fi

GIT_LS_FILES='git ls-files -c -o --exclude-standard --deduplicate'

check_ansible_vault() {
    local IFS=' '
    local vault_files

    vault_files=$(
        ${GIT_LS_FILES} -z -- '**_vars/**vault.'{yaml,yml,json} '*.'{key,csr,p12} \
            '**/'{private,privkey,\*[-.]key}.pem \
            | xargs -0 -r grep --files-without-match -- $'^$ANSIBLE_VAULT'
    ) ||:

    if [[ "$vault_files" != "" ]]; then
        echo -e "${COLOR_RED}Clear-text private keys or vault files!${COLOR_CLEAR}" >&2
        echo "$vault_files"
        return 1
    fi

    echo -e "${COLOR_GREEN}ansible-vault files check passed.${COLOR_CLEAR}" >&2
    return 0
}

check_ansible_lint() {
    # Disable ansible-vault for ansible-lint. Exclude *vault.yml in .ansible-lint!
    export ANSIBLE_ASK_VAULT_PASS='False'
    if [[ -z "${ANSIBLE_VAULT_PASSWORD_FILE-}" && -r /etc/hostname ]]; then
        export ANSIBLE_VAULT_PASSWORD_FILE='/etc/hostname'
        export ANSIBLE_VAULT_IDENTITY_LIST=''
    fi

    ansible-lint
}

_check_targets_stub() {
    local targets_func="$1"
    shift

    if ! command -v "$1" >/dev/null 2>&1; then
        echo -e "${COLOR_YELLOW}${1} is not installed! skipping...${COLOR_CLEAR}" >&2
        return 0
    fi

    local IFS=$'\n'
    local targets
    read -r -a targets -d '' < <("$targets_func" | sort -u) ||:
    IFS=' '

    if [[ -n "${targets-}" ]]; then
        "$@" "${targets[@]}" || {
            echo -e "${COLOR_RED}ERROR: $*${COLOR_CLEAR}" >&2
            return 1
        }
        echo -e "${COLOR_GREEN}${1} passed${COLOR_CLEAR}: on ${#targets[@]} files." >&2
    fi
}

# shellcheck disable=SC2329,SC2317 # function is never invoked
_shellcheck_targets() {
    local IFS=' '

    ${GIT_LS_FILES} -- '*.'{sh,bash,ksh,zsh} '**/*shrc' '**/.*profile'
    ${GIT_LS_FILES} -z -- '**scripts/*' '**/bin/*' '**/sbin/*' ':!:*.'{j2,jinja2,jinja} \
        | xargs -0 -r awk -- 'FNR>1 {nextfile} /^#![^ ]+[/ ](sh|bash|ksh|zsh)$/ {print FILENAME; nextfile}'
}

check_shellcheck() {
    _check_targets_stub _shellcheck_targets shellcheck --
}

# shellcheck disable=SC2329,SC2317 # function is never invoked
_python_targets() {
    local IFS=' '

    ${GIT_LS_FILES} -- '*.py'
    ${GIT_LS_FILES} -z -- '**scripts/*' '**/bin/*' '**/sbin/*' ':!:*.'{j2,jinja2,jinja} \
        | xargs -0 -r awk -- 'FNR>1 {nextfile} /^#![^ ]+[/ ](python3?)$/ {print FILENAME; nextfile}'
}

check_pylint() {
    _check_targets_stub _python_targets pylint --disable duplicate-code,import-error --
}

check_black() {
    _check_targets_stub _python_targets black --check -l 120 --target-version=py311 --
}

run_linters=0
# Skip linters by default and if stdin is not a terminal.
if [[ $# -eq 0 ]]; then
    if [[ -t 1 ]]; then
        exec < /dev/tty
        echo -en "${COLOR_YELLOW}Run ansible-lint and linters for scripts?${COLOR_CLEAR} [y/N]" >&2
        read -r answer
        if [[ "$answer" =~ ^[Yy] ]]; then
            run_linters=1
        fi
    fi
elif [[ "${1-}" =~ ^(-f|--force|-y|--yes)$ ]]; then
    run_linters=1
else
    echo "Usage: ${0} [-f|--force|-y|--yes]" >&2
    exit 2
fi

rc=0
if [[ "$run_linters" -ne 0 ]]; then
    check_ansible_lint || (( rc=1 ))
    check_shellcheck   || (( rc=1 ))
    check_pylint       || (( rc=1 ))
    check_black        || (( rc=1 ))
fi

check_ansible_vault    || (( rc=1 ))
exit $rc

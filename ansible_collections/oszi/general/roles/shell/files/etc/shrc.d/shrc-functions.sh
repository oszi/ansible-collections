# shellcheck shell=sh

py() {
    if python3 -c "import importlib.util, sys; \
sys.exit(int(importlib.util.find_spec('IPython') is None))" >/dev/null 2>&1; then
        python3 -m IPython "$@"
    else
        python3 "$@"
    fi
}

_answer_yes() {
    printf "# %s [y/N]" "${1:-Answer yes}" >&2
    read -r answer
    echo "$answer" | grep -iq '^Y'
}

_FIND_ENCRYPTED_REGEX='.*\.\(aes\|asc\|gpg\|enc\|encrypted\|kdbx?\)$'

_find_clear() {
    find "$@" -type f -not -iregex "$_FIND_ENCRYPTED_REGEX"
}

alias find-clear='_find_clear'

_find_clear_gpg_encrypt() {
    if [ $# -eq 0 ]; then
        echo "Usage: find-clear-gpg-encrypt PATH [FIND ARGS]" >&2
        return 2
    fi

    files="$(_find_clear "$@" | tee /dev/stderr)"
    rc=1
    if [ -n "$files" ] \
        && _answer_yes "GPG encrypt the above files with default-recipient-self?" \
        && echo "$files" | xargs -d'\n' -n1 gpg -es --batch --yes --default-recipient-self --; then

        rc=0
        if _answer_yes "Delete the above clear-text files?"; then
            echo "$files" | xargs -d'\n' rm -fv --
            rc=$?
        fi
    fi
    unset files
    return $rc
}

alias find-clear-gpg-encrypt='_find_clear_gpg_encrypt'

_find_encrypted() {
    find "$@" -type f -iregex "$_FIND_ENCRYPTED_REGEX"
}

alias find-encrypted='_find_encrypted'

_find_latest() {
    find "$@" -type f -printf '%T@\0%p\0' \
        | awk '{if($0>max){max=$0;getline last} else getline} END{print last}' RS='\0'
}

alias find-latest='_find_latest'

_sort_u_file() {
    if [ -f "$1" ]; then
        sort -u "$1" > "$1"~
        mv "$1"~ "$1"
    else
        echo 'Usage: sort-u-file <file>' >&2
        return 2
    fi
}

alias sort-u-file='_sort_u_file'

_PROXY_ENV_VARS='all_proxy http_proxy https_proxy ftp_proxy ALL_PROXY HTTP_PROXY HTTPS_PROXY FTP_PROXY'

if [ -z "${no_proxy-}" ]; then
    export no_proxy='localhost,.local,.localdomain'
    export NO_PROXY="$no_proxy"
fi

_proxy_set() {
    if echo "${1-}" | grep -q '://'; then
        for _env_var in $_PROXY_ENV_VARS; do export "$_env_var"="$1"; done
        env | grep -i '_proxy=' | sort
    else
        echo 'Usage: proxy-set proto://host:port' >&2
        return 2
    fi
}

alias proxy-set='_proxy_set'
alias proxy-set-lo5h='_proxy_set socks5h://localhost:1080'
alias proxy-unset='unset $_PROXY_ENV_VARS'

# Abort here if ssh client is absent.
command -v ssh >/dev/null 2>&1 || return

_ssh_proxied() {
    if [ -n "${all_proxy-}" ]; then
        _ssh_proxy="$(echo "$all_proxy" | awk -F'://' '{print $NF}')"
        _ssh_proxy_type="$(echo "$all_proxy" | grep -Eo '^(http|socks[45])')"  # only supported
    else
        _ssh_proxy='localhost:1080'
        _ssh_proxy_type='socks5'
    fi
    _ssh_cmd="$1"
    shift
    "$_ssh_cmd" -o "ProxyCommand=nc --proxy=\"$_ssh_proxy\" --proxy-type=\"$_ssh_proxy_type\" %h %p" "$@"
}

alias ssh-proxied='_ssh_proxied ssh'
alias scp-proxied='_ssh_proxied scp'

_gpg_ssh_setup() {
    gpg -K --with-keygrip # creates ~/.gnupg

    if ! grep -E '^enable-ssh-support' ~/.gnupg/gpg-agent.conf >/dev/null 2>&1; then
        echo 'enable-ssh-support' >> ~/.gnupg/gpg-agent.conf
        gpg-connect-agent reloadagent /bye >/dev/null
    fi

    if systemctl is-enabled pcscd pcscd.socket >/dev/null 2>&1; then
        if ! grep -E '^disable-ccid' ~/.gnupg/scdaemon.conf >/dev/null 2>&1; then
            echo 'disable-ccid' >> ~/.gnupg/scdaemon.conf
            gpg-connect-agent reloadagent /bye >/dev/null
        fi
    fi

    SSH_AUTH_SOCK="$(gpgconf --list-dirs agent-ssh-socket)"
    export SSH_AUTH_SOCK
    gpg-connect-agent updatestartuptty /bye >/dev/null

    echo "[ssh-add] Add [A] keygrips to ~/.gnupg/sshcontrol" >&2
    echo "[~/.ssh/config] IdentityAgent ${SSH_AUTH_SOCK}" >&2
    ssh-add -L
}

alias gpg-ssh-setup='_gpg_ssh_setup'

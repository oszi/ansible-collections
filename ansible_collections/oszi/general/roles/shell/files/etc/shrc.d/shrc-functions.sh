# shellcheck shell=sh

if command -v python3 >/dev/null 2>&1; then
    py() {
        if python3 -c "import importlib.util, sys; \
sys.exit(int(importlib.util.find_spec('IPython') is None))" >/dev/null 2>&1; then
            python3 -m IPython "$@"
        else
            python3 "$@"
        fi
    }
fi

if command -v sort >/dev/null 2>&1; then
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
fi

_answer_yes() {
    printf "# %s [y/N]" "${1:-Answer yes}" >&2
    read -r answer
    echo "$answer" | grep -iq '^Y'
}

if command -v find >/dev/null 2>&1; then
    _find_latest() {
        find "$@" -type f -printf '%T@\0%p\0' \
            | awk '{if($0>max){max=$0;getline last} else getline} END{print last}' RS='\0'
    }

    alias find-latest='_find_latest'

    _FIND_ENCRYPTED_REGEX='.*\.\(aes\|asc\|gpg\|enc\|encrypted\|kdbx?\)$'

    _find_not_encrypted() {
        find "$@" -type f -not -iregex "$_FIND_ENCRYPTED_REGEX"
    }

    alias find-not-encrypted='_find_not_encrypted'

    _find_encrypted() {
        find "$@" -type f -iregex "$_FIND_ENCRYPTED_REGEX"
    }

    alias find-encrypted='_find_encrypted'

    if command -v gpg >/dev/null 2>&1; then
        _find_gpg_encrypt_self() {
            if [ $# -eq 0 ]; then
                echo "Usage: find-gpg-encrypt-self PATH [FIND ARGS]" >&2
                return 2
            fi

            files="$(_find_not_encrypted "$@" | tee /dev/stderr)"
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

        alias find-gpg-encrypt-self='_find_gpg_encrypt_self'
    fi
fi

if command -v gpg-connect-agent >/dev/null 2>&1; then
    _gpg_reload_agent() {
        gpg-connect-agent reloadagent /bye
        gpg-connect-agent updatestartuptty /bye
    }

    alias gpg-reload-agent='_gpg_reload_agent'

    if command -v ssh >/dev/null 2>&1; then
        _gpg_ssh_setup() {
            gpg -K --with-keygrip # init ~/.gnupg

            if ! grep -E '^enable-ssh-support' ~/.gnupg/gpg-agent.conf >/dev/null 2>&1; then
                echo 'enable-ssh-support' >> ~/.gnupg/gpg-agent.conf
                gpg-connect-agent reloadagent /bye >/dev/null
            fi

            if systemctl is-enabled pcscd >/dev/null 2>&1; then
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
        }

        alias gpg-ssh-setup='_gpg_ssh_setup'
    fi
fi

# Fix uninitialized VTE in non-login shells for VTE-based desktop terminals.
# shellcheck shell=sh disable=SC1091 # not following input sources
# shellcheck disable=SC3010,SC3044,SC3062 # in POSIX [[ ]] and shopt are undefined

if [ -n "${BASH_VERSION-}" ]; then
    if shopt -q login_shell; then
        return
    fi
    # -> Bash non-login shell.

elif [ -n "${ZSH_VERSION-}" ] && [ "$(emulate)" = "zsh" ]; then
    if [[ -o login ]]; then
        return
    fi
    # -> ZSH non-login shell.

else
    return
fi

if [ -f /etc/profile.d/vte.sh ]; then
    . /etc/profile.d/vte.sh
elif [ -f /etc/profile.d/vte-2.91.sh ]; then
    . /etc/profile.d/vte-2.91.sh
fi

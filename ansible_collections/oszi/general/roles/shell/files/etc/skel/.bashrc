# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

if [ -f /etc/bashrc ]; then
    . /etc/bashrc
elif [ -f /etc/bash.bashrc ]; then
    . /etc/bash.bashrc
fi

source_glob() {
    for rc in "$@"; do
        if [ -r "$rc" ]; then
            if [ -n "${PS1-}" ]; then
                . "$rc"
            else
                . "$rc" >/dev/null
            fi
        fi
    done
    unset rc
}

if [ -z "${POSIXLY_CORRECT-}" ]; then
    source_glob /etc/shrc.d/*.sh /etc/shrc.d/*.bash \
        ~/.bashrc.d/* ~/.bash_aliases
else
    source_glob /etc/shrc.d/*.sh
fi

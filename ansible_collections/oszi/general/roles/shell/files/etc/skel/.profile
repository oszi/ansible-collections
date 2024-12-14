# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed skel

# This file is not read by bash if ~/.bash_profile or ~/.bash_login exists.

if [ -d /etc/shrc.d ]; then
    for rc in /etc/shrc.d/*.sh; do
        if [ -r "$rc" ]; then
            if [ -n "${PS1-}" ]; then
                . "$rc"
            else
                . "$rc" >/dev/null
            fi
        fi
    done
    unset rc
fi

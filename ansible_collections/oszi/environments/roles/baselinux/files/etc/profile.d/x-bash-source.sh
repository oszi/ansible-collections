# shellcheck shell=sh disable=SC1090 # non-constant source

# Source *.bash files as Debian/RedHat only source *.sh
if [ -n "${BASH_VERSION:-}" ]; then
    for i in /etc/profile.d/*.bash; do
        if [ -r "$i" ]; then
            . "$i"
        fi
    done
fi

# Ensure nested shells are login shells too
alias bash='bash -l'

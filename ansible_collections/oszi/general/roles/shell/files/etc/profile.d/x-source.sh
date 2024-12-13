# shellcheck shell=sh disable=SC1090 # non-constant source

case $- in
    *i*) ;;
      *) return ;;
esac

# Source .bash files as Debian/RedHat only source .sh
if [ -n "${BASH_VERSION-}" ]; then
    for i in /etc/profile.d/*.bash; do
        if [ -r "$i" ]; then
            . "$i"
        fi
    done
    unset i
fi

# Some compatibility with the old /bin/sh
if [ -z "${BASH_VERSION-}" ]; then
    for rc in /etc/bashrc.d/x-*.sh; do
        if [ -r "$rc" ]; then
            . "$rc"
        fi
    done
    unset rc
fi

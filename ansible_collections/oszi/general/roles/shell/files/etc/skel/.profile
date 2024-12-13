# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed .profile

# This file is not read by bash if ~/.bash_profile or ~/.bash_login exists.

case $- in
    *i*) ;;
      *) return ;;
esac

# Strictly posix-compliant files [x-*.sh]
for rc in /etc/bashrc.d/x-*.sh "$HOME"/.bashrc.d/x-*.sh; do
    if [ -r "$rc" ]; then
        . "$rc"
    fi
done
unset rc

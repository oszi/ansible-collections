# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed .profile

# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login exists.

case $- in
    *i*) ;;
      *) return ;;
esac

for rc in /etc/bashrc.d/x-*.sh "$HOME"/.bashrc.d/x-*.sh; do
    if [ -r "$rc" ]; then
        . "$rc"
    fi
done
unset rc

# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed .bash_profile

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

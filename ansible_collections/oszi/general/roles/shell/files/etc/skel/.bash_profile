# Ansible managed skel
# shellcheck shell=sh disable=SC1090 # non-constant source

if [ -f ~/.profile ]; then
    . ~/.profile
fi

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

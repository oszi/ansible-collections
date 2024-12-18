# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed skel

if [ -f ~/.profile ]; then
    . ~/.profile
fi

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

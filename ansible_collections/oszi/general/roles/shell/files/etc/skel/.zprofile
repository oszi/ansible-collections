# shellcheck shell=sh disable=SC1090 # non-constant source
# ansible managed skel

# .zshenv is always sourced
# .zshrc is sourced in interactive mode

if [ -f ~/.profile ]; then
    . ~/.profile
fi

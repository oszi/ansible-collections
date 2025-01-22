# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

# See also /etc/{zsh/,}zshrc from the distribution.
# Sequence: zshenv > zprofile* > zshrc* > zlogin > zlogout

. /etc/shrc

if [ -d ~/.zshrc.d ]; then
    source_glob ~/.zshrc.d/*
fi

# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

autoload -Uz +X compinit && compinit
autoload -Uz +X bashcompinit && bashcompinit
autoload -Uz +X colors && colors

. /etc/shrc

if [ -d ~/.zshrc.d ]; then
    source_glob ~/.zshrc.d/*
fi

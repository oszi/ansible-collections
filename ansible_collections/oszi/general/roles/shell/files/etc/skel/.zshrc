# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

autoload -U compinit
compinit

if [ -d /etc/shrc.d ]; then
    for rc in /etc/shrc.d/*.sh /etc/shrc.d/*.zsh; do
        if [ -r "$rc" ]; then
            . "$rc"
        fi
    done
    unset rc
fi

if [ -d ~/.zshrc.d ]; then
    for rc in ~/.zshrc.d/*; do
        if [ -r "$rc" ]; then
            . "$rc"
        fi
    done
    unset rc
fi

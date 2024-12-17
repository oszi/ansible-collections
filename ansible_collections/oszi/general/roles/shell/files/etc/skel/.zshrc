# shellcheck shell=sh disable=SC1090,SC1091 # non-constant source
# ansible managed skel

# Customize your env in ~/.zshenv
if [ -f "${ZSH:-$HOME/.oh-my-zsh}/oh-my-zsh.sh" ]; then
    . "${ZSH:-$HOME/.oh-my-zsh}/oh-my-zsh.sh"

# Plain ZSH init
else
    autoload -Uz +X compinit && compinit
    autoload -Uz +X bashcompinit && bashcompinit
fi

# After Oh My ZSH!
. /etc/shrc

if [ -d ~/.zshrc.d ]; then
    source_glob ~/.zshrc.d/*
fi

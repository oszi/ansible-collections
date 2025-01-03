# shellcheck shell=sh

autoload -Uz +X compinit && compinit
autoload -Uz +X bashcompinit && bashcompinit

zstyle ':completion:*' completer _complete _ignored _files

# shellcheck shell=bash disable=SC2296 # zsh is unsupported
# shellcheck disable=SC2016,SC2034 # single quotes, variable appears unused

autoload -Uz +X compinit && compinit
autoload -Uz +X bashcompinit && bashcompinit

setopt COMPLETE_IN_WORD

zstyle ':completion:*' completer _complete _match _prefix _approximate _files
zstyle ':completion:*' verbose yes

zstyle ':completion:*:approximate:*' max-errors 'reply=($((($#PREFIX+$#SUFFIX)/3)) numeric)'

zstyle ':completion:*:*:kill:*' command 'ps -u $UID -o pid=,tty=,cmd='
zstyle ':completion:*:*:kill:*' menu yes select

zstyle ':completion:*:default' list-colors "${(s.:.)LS_COLORS}"
